from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request, Query, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bson import ObjectId
from bson.json_util import dumps
import jwt
import bcrypt
import re
import hashlib
import asyncio
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'grovellows-secure-key-2025-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7  # Reduced for security

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)

# Background Scheduler for auto-scraping
scheduler = AsyncIOScheduler()

# Create the main app
app = FastAPI(
    title="GroVELLOWS API",
    description="German Construction Tender Tracking Platform - GDPR Compliant",
    version="2.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ SECURITY HELPERS ============

def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent injection attacks"""
    if not text:
        return ""
    # Remove potentially dangerous characters
    text = re.sub(r'[<>"\';]', '', text)
    # Limit length
    return text[:5000]

def validate_password(password: str) -> bool:
    """Validate password strength - GDPR compliance"""
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    return True

# ============ ROLE PERMISSIONS ============

ROLE_PERMISSIONS = {
    "Director": ["read", "write", "delete", "admin", "share", "scrape"],
    "Partner": ["read", "write", "delete", "admin", "share"],
    "Senior Project Manager": ["read", "write", "share"],
    "Project Manager": ["read", "write", "share"],
    "HR": ["read", "share"],
    "Intern": ["read"],
}

def check_permission(user: dict, permission: str) -> bool:
    """Check if user has specific permission"""
    role = user.get("role", "Intern")
    allowed = ROLE_PERMISSIONS.get(role, [])
    return permission in allowed

# ============ MODELS ============

class UserRole(str):
    PROJECT_MANAGER = "Project Manager"
    SENIOR_PROJECT_MANAGER = "Senior Project Manager"
    INTERN = "Intern"
    HR = "HR"
    PARTNER = "Partner"
    DIRECTOR = "Director"

class EmployeeProfile(BaseModel):
    """Extended employee profile for connections feature"""
    department: Optional[str] = None
    expertise: List[str] = []
    previous_projects: List[str] = []
    regions_experience: List[str] = []
    authorities_experience: List[str] = []  # Contracting authorities they've worked with
    phone: Optional[str] = None
    office_location: Optional[str] = None

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str
    linkedin_url: Optional[str] = None
    department: Optional[str] = None
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
    
    @validator('email')
    def email_sanitize(cls, v):
        return v.lower().strip()

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: str
    linkedin_url: Optional[str] = None
    department: Optional[str] = None
    profile: Optional[EmployeeProfile] = None
    notification_preferences: dict = Field(default_factory=lambda: {
        "new_tenders": True,
        "status_changes": True,
        "ipa_tenders": True,
        "project_management": True,
        "daily_digest": True
    })
    gdpr_consent: Optional[dict] = None
    gdpr_consent_date: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class TenderStatus(str):
    NEW = "New"
    IN_PROGRESS = "In Progress"
    CLOSED = "Closed"

class TenderCategory(str):
    IPA = "IPA"
    IPD = "IPD"
    INTEGRATED_PM = "Integrated Project Management"
    PROJECT_MANAGEMENT = "Project Management"
    RISK_MANAGEMENT = "Risk Management"
    LEAN_MANAGEMENT = "Lean Management"
    PROCUREMENT_MANAGEMENT = "Procurement Management"
    ORGANIZATION_ALIGNMENT = "Organization Alignment Workshops"
    CONSTRUCTION_SUPERVISION = "Construction Supervision"
    CHANGE_ORDER_MANAGEMENT = "Change Order Management"
    COST_MANAGEMENT = "Cost Management"
    TENDERING_PROCESS = "Tendering Process"
    PROJECT_COMPLETION = "Project Completion"
    HANDOVER_DOCUMENTATION = "Handover Documentation"
    GENERAL = "General"

class Tender(BaseModel):
    id: Optional[str] = None
    title: str
    description: str
    budget: Optional[str] = None
    deadline: datetime
    location: str
    project_type: str
    contracting_authority: str
    participants: List[str] = []
    contact_details: dict = {}
    tender_date: datetime
    category: str
    building_typology: Optional[str] = None  # NEW
    platform_source: str
    platform_url: str
    status: str = TenderStatus.NEW
    is_applied: bool = False  # NEW
    applied_date: Optional[datetime] = None  # NEW
    application_status: str = "Not Applied"  # NEW: Not Applied, Awaiting Results, Won, Lost
    result_date: Optional[datetime] = None  # NEW
    linkedin_connections: List[dict] = []  # NEW
    duplicate_sources: List[str] = []  # NEW: Other platforms with same tender
    sharepoint_folder: Optional[str] = None  # NEW
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TenderCreate(BaseModel):
    title: str
    description: str
    budget: Optional[str] = None
    deadline: datetime
    location: str
    project_type: str
    contracting_authority: str
    participants: List[str] = []
    contact_details: dict = {}
    tender_date: datetime
    category: str
    platform_source: str
    platform_url: str

class TenderUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

class Favorite(BaseModel):
    user_id: str
    tender_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Share(BaseModel):
    tender_id: str
    shared_by: str
    shared_with: List[str]
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ShareRequest(BaseModel):
    tender_id: str
    shared_with: List[str]
    message: Optional[str] = None

class TenderDocument(BaseModel):
    tender_id: str
    user_id: str
    document_data: dict
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class NotificationPreferences(BaseModel):
    new_tenders: bool = True
    status_changes: bool = True
    ipa_tenders: bool = True
    project_management: bool = True
    daily_digest: bool = True

class NewsArticle(BaseModel):
    id: Optional[str] = None
    title: str
    description: str
    content: str
    source: str
    url: str
    project_name: Optional[str] = None
    location: Optional[str] = None
    issue_type: str  # "stuck", "underperforming", "opportunity", "general"
    severity: str  # "high", "medium", "low"
    published_date: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DeveloperProject(BaseModel):
    id: Optional[str] = None
    developer_name: str
    developer_url: str
    project_name: str
    description: str
    location: str
    budget: Optional[str] = None
    project_type: str
    status: str  # "planning", "ongoing", "delayed", "completed"
    start_date: datetime
    expected_completion: datetime
    actual_completion: Optional[datetime] = None
    timeline_phases: List[dict] = []  # [{"phase": "Foundation", "status": "completed", "date": "..."}]
    contacts: dict = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TenderPortal(BaseModel):
    id: Optional[str] = None
    name: str
    url: str
    type: str  # "public", "private"
    region: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PortalCreate(BaseModel):
    name: str
    url: str
    type: str
    region: Optional[str] = None
    description: Optional[str] = None

class PortalUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    type: Optional[str] = None
    region: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class GDPRConsent(BaseModel):
    dataProcessing: bool
    dataStorage: bool
    analytics: bool = False
    marketing: bool = False

# ============ HELPER FUNCTIONS ============

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Check if user has admin role (Director or Partner)"""
    allowed_roles = ["Director", "Partner"]
    if current_user.get("role") not in allowed_roles:
        raise HTTPException(
            status_code=403, 
            detail="Admin access required. Only Directors and Partners can access this feature."
        )
    return current_user

# ============ AUTH ENDPOINTS ============

@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserRegister):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Create user
    user_dict = {
        "email": user_data.email,
        "password": hashed_password,
        "name": user_data.name,
        "role": user_data.role,
        "linkedin_url": user_data.linkedin_url,
        "notification_preferences": {
            "new_tenders": True,
            "status_changes": True,
            "ipa_tenders": True,
            "project_management": True,
            "daily_digest": True
        },
        "created_at": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_dict)
    user_dict["_id"] = result.inserted_id
    
    # Create token
    token = create_access_token({"sub": str(result.inserted_id)})
    
    user_response = User(
        id=str(result.inserted_id),
        email=user_dict["email"],
        name=user_dict["name"],
        role=user_dict["role"],
        linkedin_url=user_dict.get("linkedin_url"),
        notification_preferences=user_dict["notification_preferences"],
        created_at=user_dict["created_at"]
    )
    
    return Token(access_token=token, token_type="bearer", user=user_response)

@api_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": str(user["_id"])})
    
    user_response = User(
        id=str(user["_id"]),
        email=user["email"],
        name=user["name"],
        role=user["role"],
        linkedin_url=user.get("linkedin_url"),
        notification_preferences=user.get("notification_preferences", {}),
        created_at=user["created_at"]
    )
    
    return Token(access_token=token, token_type="bearer", user=user_response)

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: dict = Depends(get_current_user)):
    return User(
        id=str(current_user["_id"]),
        email=current_user["email"],
        name=current_user["name"],
        role=current_user["role"],
        linkedin_url=current_user.get("linkedin_url"),
        notification_preferences=current_user.get("notification_preferences", {}),
        created_at=current_user["created_at"]
    )

@api_router.put("/auth/preferences")
async def update_preferences(
    preferences: NotificationPreferences,
    current_user: dict = Depends(get_current_user)
):
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"notification_preferences": preferences.dict()}}
    )
    return {"message": "Preferences updated"}

@api_router.put("/auth/linkedin")
async def update_linkedin(
    linkedin_url: str,
    current_user: dict = Depends(get_current_user)
):
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"linkedin_url": linkedin_url}}
    )
    return {"message": "LinkedIn URL updated"}

@api_router.post("/auth/gdpr-consent")
async def save_gdpr_consent(
    consent: GDPRConsent,
    current_user: dict = Depends(get_current_user)
):
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {
            "gdpr_consent": consent.dict(),
            "gdpr_consent_date": datetime.utcnow()
        }}
    )
    return {"message": "GDPR consent saved"}

@api_router.get("/auth/gdpr-consent")
async def get_gdpr_consent(
    current_user: dict = Depends(get_current_user)
):
    return {
        "consent": current_user.get("gdpr_consent"),
        "consent_date": current_user.get("gdpr_consent_date")
    }

# ============ TENDER ENDPOINTS ============

@api_router.get("/tenders", response_model=List[Tender])
async def get_tenders(
    status: Optional[str] = None,
    category: Optional[str] = None,
    location: Optional[str] = None,
    search: Optional[str] = None,
    building_typology: Optional[str] = None,
    is_applied: Optional[bool] = None,
    application_status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    if building_typology:
        query["building_typology"] = building_typology
    if is_applied is not None:
        query["is_applied"] = is_applied
    if application_status:
        query["application_status"] = application_status
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    tenders = await db.tenders.find(query).sort("created_at", -1).to_list(1000)
    
    return [Tender(
        id=str(tender["_id"]),
        **{k: v for k, v in tender.items() if k != "_id"}
    ) for tender in tenders]

@api_router.get("/tenders/{tender_id}", response_model=Tender)
async def get_tender(
    tender_id: str,
    current_user: dict = Depends(get_current_user)
):
    tender = await db.tenders.find_one({"_id": ObjectId(tender_id)})
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    return Tender(
        id=str(tender["_id"]),
        **{k: v for k, v in tender.items() if k != "_id"}
    )

@api_router.post("/tenders", response_model=Tender)
async def create_tender(
    tender_data: TenderCreate,
    current_user: dict = Depends(get_current_user)
):
    tender_dict = tender_data.dict()
    tender_dict["status"] = TenderStatus.NEW
    tender_dict["created_at"] = datetime.utcnow()
    tender_dict["updated_at"] = datetime.utcnow()
    
    result = await db.tenders.insert_one(tender_dict)
    tender_dict["_id"] = result.inserted_id
    
    return Tender(
        id=str(result.inserted_id),
        **{k: v for k, v in tender_dict.items() if k != "_id"}
    )

@api_router.put("/tenders/{tender_id}")
async def update_tender(
    tender_id: str,
    update_data: TenderUpdate,
    current_user: dict = Depends(get_current_user)
):
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow()
    
    result = await db.tenders.update_one(
        {"_id": ObjectId(tender_id)},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    return {"message": "Tender updated"}

# ============ APPLICATION TRACKING ENDPOINTS ============

class ApplicationUpdate(BaseModel):
    is_applied: bool = True
    application_status: str = "Awaiting Results"

@api_router.post("/tenders/{tender_id}/apply")
async def apply_to_tender(
    tender_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a tender as applied"""
    tender = await db.tenders.find_one({"_id": ObjectId(tender_id)})
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    update_dict = {
        "is_applied": True,
        "applied_date": datetime.utcnow(),
        "application_status": "Awaiting Results",
        "updated_at": datetime.utcnow()
    }
    
    # Track who applied (add user to list if not already there)
    applied_by = tender.get("applied_by", [])
    user_id = str(current_user["_id"])
    if user_id not in applied_by:
        applied_by.append(user_id)
        update_dict["applied_by"] = applied_by
    
    await db.tenders.update_one(
        {"_id": ObjectId(tender_id)},
        {"$set": update_dict}
    )
    
    return {"message": "Application recorded successfully", "applied_date": update_dict["applied_date"]}

@api_router.delete("/tenders/{tender_id}/apply")
async def unapply_tender(
    tender_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove application from tender"""
    tender = await db.tenders.find_one({"_id": ObjectId(tender_id)})
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    # Remove user from applied_by list
    applied_by = tender.get("applied_by", [])
    user_id = str(current_user["_id"])
    if user_id in applied_by:
        applied_by.remove(user_id)
    
    # If no one has applied anymore, reset the application status
    update_dict = {
        "applied_by": applied_by,
        "updated_at": datetime.utcnow()
    }
    
    if len(applied_by) == 0:
        update_dict["is_applied"] = False
        update_dict["application_status"] = "Not Applied"
        update_dict["applied_date"] = None
    
    await db.tenders.update_one(
        {"_id": ObjectId(tender_id)},
        {"$set": update_dict}
    )
    
    return {"message": "Application removed successfully"}

@api_router.put("/tenders/{tender_id}/application-status")
async def update_application_status(
    tender_id: str,
    status: str,
    current_user: dict = Depends(get_current_user)
):
    """Update application status (Awaiting Results, Won, Lost)"""
    valid_statuses = ["Not Applied", "Awaiting Results", "Won", "Lost"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    update_dict = {
        "application_status": status,
        "updated_at": datetime.utcnow()
    }
    
    # If marking as Won or Lost, record the result date
    if status in ["Won", "Lost"]:
        update_dict["result_date"] = datetime.utcnow()
    
    result = await db.tenders.update_one(
        {"_id": ObjectId(tender_id)},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    return {"message": f"Application status updated to {status}"}

@api_router.get("/my-applications")
async def get_my_applications(
    application_status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all tenders the current user has applied to"""
    user_id = str(current_user["_id"])
    
    query = {"applied_by": user_id}
    if application_status:
        query["application_status"] = application_status
    
    tenders = await db.tenders.find(query).sort("applied_date", -1).to_list(1000)
    
    return [Tender(
        id=str(tender["_id"]),
        **{k: v for k, v in tender.items() if k != "_id"}
    ) for tender in tenders]

# ============ LINKEDIN CONNECTIONS ENDPOINTS ============

class LinkedInConnection(BaseModel):
    name: str
    profile_url: str
    role: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None

@api_router.post("/tenders/{tender_id}/linkedin")
async def add_linkedin_connection(
    tender_id: str,
    connection: LinkedInConnection,
    current_user: dict = Depends(get_current_user)
):
    """Add a LinkedIn connection to a tender"""
    tender = await db.tenders.find_one({"_id": ObjectId(tender_id)})
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    connection_dict = connection.dict()
    connection_dict["added_by"] = str(current_user["_id"])
    connection_dict["added_at"] = datetime.utcnow()
    
    await db.tenders.update_one(
        {"_id": ObjectId(tender_id)},
        {"$push": {"linkedin_connections": connection_dict}}
    )
    
    return {"message": "LinkedIn connection added successfully"}

@api_router.delete("/tenders/{tender_id}/linkedin/{connection_index}")
async def remove_linkedin_connection(
    tender_id: str,
    connection_index: int,
    current_user: dict = Depends(get_current_user)
):
    """Remove a LinkedIn connection from a tender"""
    tender = await db.tenders.find_one({"_id": ObjectId(tender_id)})
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    connections = tender.get("linkedin_connections", [])
    if connection_index < 0 or connection_index >= len(connections):
        raise HTTPException(status_code=400, detail="Invalid connection index")
    
    connections.pop(connection_index)
    
    await db.tenders.update_one(
        {"_id": ObjectId(tender_id)},
        {"$set": {"linkedin_connections": connections}}
    )
    
    return {"message": "LinkedIn connection removed successfully"}

# ============ FAVORITES ENDPOINTS ============

@api_router.post("/favorites/{tender_id}")
async def add_favorite(
    tender_id: str,
    current_user: dict = Depends(get_current_user)
):
    # Check if already favorited
    existing = await db.favorites.find_one({
        "user_id": str(current_user["_id"]),
        "tender_id": tender_id
    })
    
    if existing:
        return {"message": "Already in favorites"}
    
    favorite = {
        "user_id": str(current_user["_id"]),
        "tender_id": tender_id,
        "created_at": datetime.utcnow()
    }
    
    await db.favorites.insert_one(favorite)
    return {"message": "Added to favorites"}

@api_router.delete("/favorites/{tender_id}")
async def remove_favorite(
    tender_id: str,
    current_user: dict = Depends(get_current_user)
):
    await db.favorites.delete_one({
        "user_id": str(current_user["_id"]),
        "tender_id": tender_id
    })
    return {"message": "Removed from favorites"}

@api_router.get("/favorites")
async def get_favorites(
    current_user: dict = Depends(get_current_user)
):
    favorites = await db.favorites.find(
        {"user_id": str(current_user["_id"])}
    ).to_list(1000)
    
    tender_ids = [ObjectId(f["tender_id"]) for f in favorites]
    tenders = await db.tenders.find({"_id": {"$in": tender_ids}}).to_list(1000)
    
    return [Tender(
        id=str(tender["_id"]),
        **{k: v for k, v in tender.items() if k != "_id"}
    ) for tender in tenders]

# ============ SHARE ENDPOINTS ============

@api_router.post("/share")
async def share_tender(
    share_data: ShareRequest,
    current_user: dict = Depends(get_current_user)
):
    share_dict = share_data.dict()
    share_dict["shared_by"] = str(current_user["_id"])
    share_dict["created_at"] = datetime.utcnow()
    
    await db.shares.insert_one(share_dict)
    return {"message": "Tender shared successfully"}

@api_router.get("/shares")
async def get_shares(
    current_user: dict = Depends(get_current_user)
):
    shares = await db.shares.find(
        {"shared_with": str(current_user["_id"])}
    ).sort("created_at", -1).to_list(1000)
    
    # Convert ObjectId to string for JSON serialization
    for share in shares:
        share["id"] = str(share["_id"])
        del share["_id"]
    
    return shares

# ============ USERS ENDPOINTS ============

@api_router.get("/users", response_model=List[User])
async def get_users(
    current_user: dict = Depends(get_current_user)
):
    users = await db.users.find().to_list(1000)
    
    return [User(
        id=str(user["_id"]),
        email=user["email"],
        name=user["name"],
        role=user["role"],
        linkedin_url=user.get("linkedin_url"),
        notification_preferences=user.get("notification_preferences", {}),
        created_at=user["created_at"]
    ) for user in users]

# ============ NEWS ENDPOINTS ============

@api_router.get("/news")
async def get_news(
    issue_type: Optional[str] = None,
    severity: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    
    if issue_type:
        query["issue_type"] = issue_type
    if severity:
        query["severity"] = severity
    
    news = await db.news.find(query).sort("published_date", -1).to_list(1000)
    
    return [NewsArticle(
        id=str(article["_id"]),
        **{k: v for k, v in article.items() if k != "_id"}
    ) for article in news]

@api_router.get("/news/{news_id}")
async def get_news_article(
    news_id: str,
    current_user: dict = Depends(get_current_user)
):
    article = await db.news.find_one({"_id": ObjectId(news_id)})
    if not article:
        raise HTTPException(status_code=404, detail="News article not found")
    
    return NewsArticle(
        id=str(article["_id"]),
        **{k: v for k, v in article.items() if k != "_id"}
    )

# ============ DEVELOPER PROJECTS ENDPOINTS ============

@api_router.get("/developer-projects")
async def get_developer_projects(
    status: Optional[str] = None,
    developer: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    
    if status:
        query["status"] = status
    if developer:
        query["developer_name"] = {"$regex": developer, "$options": "i"}
    
    projects = await db.developer_projects.find(query).sort("updated_at", -1).to_list(1000)
    
    return [DeveloperProject(
        id=str(project["_id"]),
        **{k: v for k, v in project.items() if k != "_id"}
    ) for project in projects]

@api_router.get("/developer-projects/{project_id}")
async def get_developer_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    project = await db.developer_projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return DeveloperProject(
        id=str(project["_id"]),
        **{k: v for k, v in project.items() if k != "_id"}
    )

# ============ ADMIN: PORTAL MANAGEMENT ENDPOINTS ============

@api_router.get("/admin/portals")
async def get_portals(
    admin_user: dict = Depends(require_admin)
):
    """Get all tender portals (Admin only)"""
    portals = await db.portals.find().sort("name", 1).to_list(1000)
    
    return [TenderPortal(
        id=str(portal["_id"]),
        **{k: v for k, v in portal.items() if k != "_id"}
    ) for portal in portals]

@api_router.post("/admin/portals")
async def create_portal(
    portal_data: PortalCreate,
    admin_user: dict = Depends(require_admin)
):
    """Create new tender portal (Admin only)"""
    portal_dict = portal_data.dict()
    portal_dict["is_active"] = True
    portal_dict["created_at"] = datetime.utcnow()
    portal_dict["updated_at"] = datetime.utcnow()
    
    result = await db.portals.insert_one(portal_dict)
    portal_dict["_id"] = result.inserted_id
    
    return TenderPortal(
        id=str(result.inserted_id),
        **{k: v for k, v in portal_dict.items() if k != "_id"}
    )

@api_router.put("/admin/portals/{portal_id}")
async def update_portal(
    portal_id: str,
    portal_data: PortalUpdate,
    admin_user: dict = Depends(require_admin)
):
    """Update tender portal (Admin only)"""
    update_dict = {k: v for k, v in portal_data.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow()
    
    result = await db.portals.update_one(
        {"_id": ObjectId(portal_id)},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Portal not found")
    
    return {"message": "Portal updated successfully"}

@api_router.delete("/admin/portals/{portal_id}")
async def delete_portal(
    portal_id: str,
    admin_user: dict = Depends(require_admin)
):
    """Delete tender portal (Admin only)"""
    result = await db.portals.delete_one({"_id": ObjectId(portal_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Portal not found")
    
    return {"message": "Portal deleted successfully"}

@api_router.get("/portals/public")
async def get_public_portals(
    current_user: dict = Depends(get_current_user)
):
    """Get all active portals (All users)"""
    portals = await db.portals.find({"is_active": True}).sort("name", 1).to_list(1000)
    
    return [TenderPortal(
        id=str(portal["_id"]),
        **{k: v for k, v in portal.items() if k != "_id"}
    ) for portal in portals]

# ============ SEED DATA ============

@api_router.post("/seed-data")
async def seed_sample_data():
    """Seed comprehensive sample data including tenders, news, developer projects, and portals"""
    
    # Clear existing data for fresh seed
    await db.tenders.delete_many({})
    await db.news.delete_many({})
    await db.developer_projects.delete_many({})
    await db.portals.delete_many({})
    
    # Seed tender portals
    sample_portals = [
        {
            "name": "Bund.de",
            "url": "https://service.bund.de",
            "type": "public",
            "region": "Federal",
            "description": "German Federal Government Procurement Platform",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Vergabeplattform Berlin",
            "url": "https://berlin.de/vergabeplattform",
            "type": "public",
            "region": "Berlin",
            "description": "Berlin State Tender Platform",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Vergabe Bayern",
            "url": "https://www.vergabe.bayern.de",
            "type": "public",
            "region": "Bavaria",
            "description": "Bavaria State Procurement Portal",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "e-Vergabe NRW",
            "url": "https://www.evergabe.nrw.de",
            "type": "public",
            "region": "North Rhine-Westphalia",
            "description": "North Rhine-Westphalia E-Procurement",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Vergabe Baden-Württemberg",
            "url": "https://vergabe.landbw.de",
            "type": "public",
            "region": "Baden-Württemberg",
            "description": "Baden-Württemberg Tender Platform",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Hamburg Vergabe",
            "url": "https://www.hamburg.de/wirtschaft/ausschreibungen-wirtschaft/",
            "type": "public",
            "region": "Hamburg",
            "description": "Hamburg City Procurement Portal",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Sachsen Vergabe",
            "url": "https://www.sachsen-vergabe.de",
            "type": "public",
            "region": "Saxony",
            "description": "Saxony State Tender Platform",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "TED (Tenders Electronic Daily)",
            "url": "https://ted.europa.eu",
            "type": "public",
            "region": "European",
            "description": "European Union Public Procurement Database",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        # Hospital/Klinikum Tender Portals
        {
            "name": "Universitätsklinikum Jena",
            "url": "https://www.uniklinikum-jena.de/Ausschreibungen.html",
            "type": "hospital",
            "region": "Thuringia",
            "description": "Jena University Hospital Procurement",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Universitätsklinikum Dresden",
            "url": "https://www.uniklinikum-dresden.de/de/das-klinikum/universitaetsklinikum-carl-gustav-carus/geschaeftsbereich-logistik-und-einkauf/vergabe",
            "type": "hospital",
            "region": "Saxony",
            "description": "Dresden University Hospital Procurement",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Universitätsklinikum Würzburg",
            "url": "https://www.ukw.de/ausschreibungen/startseite/",
            "type": "hospital",
            "region": "Bavaria",
            "description": "Würzburg University Hospital Procurement",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Universitätsklinikum Göttingen",
            "url": "https://www.umg.eu/ueber-uns/einkauf-logistik/ausschreibungen/",
            "type": "hospital",
            "region": "Lower Saxony",
            "description": "Göttingen University Medical Center Procurement",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Universitätsklinikum Magdeburg",
            "url": "https://www.med.uni-magdeburg.de/Ausschreibungen.html",
            "type": "hospital",
            "region": "Saxony-Anhalt",
            "description": "Magdeburg University Hospital Procurement",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Universitätsklinikum Leipzig",
            "url": "https://www.uniklinikum-leipzig.de/Seiten/ausschreibungen.aspx",
            "type": "hospital",
            "region": "Saxony",
            "description": "Leipzig University Hospital Procurement",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Universitätsklinikum Heidelberg",
            "url": "https://www.klinikum.uni-heidelberg.de/zentrale-einrichtungen/verwaltung/einkauf-technik/einkaufslogistik/ausschreibungen/",
            "type": "hospital",
            "region": "Baden-Württemberg",
            "description": "Heidelberg University Hospital Procurement",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Universitätsmedizin Mainz",
            "url": "https://www.unimedizin-mainz.de/index.php?id=43693",
            "type": "hospital",
            "region": "Rhineland-Palatinate",
            "description": "Mainz University Medical Center Procurement",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Universitätsklinikum Münster",
            "url": "https://www.ukm.de/index.php?id=ausschreibungen",
            "type": "hospital",
            "region": "North Rhine-Westphalia",
            "description": "Münster University Hospital Procurement",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Universitätsklinikum Freiburg",
            "url": "https://www.uniklinik-freiburg.de/karriere-portal/ausschreibungen.html",
            "type": "hospital",
            "region": "Baden-Württemberg",
            "description": "Freiburg University Hospital Procurement",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
    ]
    
    await db.portals.insert_many(sample_portals)
    
    # Existing tenders plus new specialized categories
    sample_tenders = [
        # Original tenders with building typologies
        {
            "title": "Neubau Wohnquartier Berlin-Mitte",
            "description": "Construction of a new residential quarter with 150 apartments, including underground parking and green spaces. IPA project delivery method.",
            "budget": "€45,000,000",
            "deadline": datetime(2025, 9, 15),
            "location": "Berlin-Mitte, Berlin",
            "project_type": "Residential Construction",
            "contracting_authority": "Senatsverwaltung für Stadtentwicklung Berlin",
            "participants": ["Hochtief AG", "Züblin AG", "BAM Deutschland AG"],
            "contact_details": {
                "name": "Dr. Klaus Müller",
                "email": "k.mueller@stadtentwicklung.berlin.de",
                "phone": "+49 30 9012 3456"
            },
            "tender_date": datetime(2025, 7, 1),
            "category": "IPA",
            "building_typology": "Residential",
            "platform_source": "Vergabeplattform Berlin",
            "platform_url": "https://berlin.de/vergabeplattform",
            "status": "New",
            "is_applied": False,
            "application_status": "Not Applied",
            "linkedin_connections": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        # New specialized tenders
        {
            "title": "Risk Management Consultant - Airport Expansion München",
            "description": "Comprehensive risk management services for Munich Airport Terminal 3 expansion. Identify, assess and mitigate construction risks. Duration: 36 months.",
            "budget": "€2,800,000",
            "deadline": datetime(2025, 8, 20),
            "location": "München, Bayern",
            "project_type": "Risk Management Services",
            "contracting_authority": "Flughafen München GmbH",
            "participants": [],
            "contact_details": {
                "name": "Dipl.-Ing. Andrea Hoffmann",
                "email": "a.hoffmann@munich-airport.de",
                "phone": "+49 89 9752 1234"
            },
            "tender_date": datetime(2025, 7, 15),
            "category": "Risk Management",
            "building_typology": "Infrastructure",
            "platform_source": "Vergabe Bayern",
            "platform_url": "https://www.vergabe.bayern.de",
            "status": "New",
            "is_applied": False,
            "application_status": "Not Applied",
            "linkedin_connections": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Lean Construction Management - Krankenhaus Charité Berlin",
            "description": "Implement lean management principles for Charité Hospital renovation project. Optimize workflows, reduce waste, improve efficiency.",
            "budget": "€1,500,000",
            "deadline": datetime(2025, 9, 1),
            "location": "Berlin",
            "project_type": "Lean Management Consulting",
            "contracting_authority": "Charité - Universitätsmedizin Berlin",
            "participants": [],
            "contact_details": {
                "name": "Prof. Dr. Stefan Weber",
                "email": "s.weber@charite.de",
                "phone": "+49 30 450 5678"
            },
            "tender_date": datetime(2025, 7, 18),
            "category": "Lean Management",
            "platform_source": "Bund.de",
            "platform_url": "https://service.bund.de",
            "status": "New",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Procurement Management - Autobahn A7 Extension",
            "description": "Strategic procurement management for A7 Autobahn extension project. Vendor selection, contract negotiation, supply chain optimization.",
            "budget": "€3,200,000",
            "deadline": datetime(2025, 8, 30),
            "location": "Hamburg - Hannover",
            "project_type": "Procurement Services",
            "contracting_authority": "Autobahn GmbH des Bundes",
            "participants": [],
            "contact_details": {
                "name": "Michael Schmidt",
                "email": "m.schmidt@autobahn.de",
                "phone": "+49 40 1234 5678"
            },
            "tender_date": datetime(2025, 7, 20),
            "category": "Procurement Management",
            "platform_source": "e-Vergabe",
            "platform_url": "https://www.evergabe-online.de",
            "status": "New",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Organization Alignment Workshop - Deutsche Bahn Headquarters",
            "description": "Facilitate organizational alignment workshops for Deutsche Bahn HQ construction project. Team building, process optimization, stakeholder management.",
            "budget": "€450,000",
            "deadline": datetime(2025, 8, 15),
            "location": "Frankfurt am Main",
            "project_type": "Organizational Consulting",
            "contracting_authority": "Deutsche Bahn AG",
            "participants": [],
            "contact_details": {
                "name": "Dr. Laura Fischer",
                "email": "l.fischer@deutschebahn.com",
                "phone": "+49 69 265 1234"
            },
            "tender_date": datetime(2025, 7, 22),
            "category": "Organization Alignment Workshops",
            "platform_source": "Deutsche eVergabe",
            "platform_url": "https://www.evergabe.de",
            "status": "New",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Construction Supervision - Wind Park Nordsee",
            "description": "On-site construction supervision for offshore wind park project. Quality control, safety monitoring, progress reporting. 24-month duration.",
            "budget": "€5,600,000",
            "deadline": datetime(2025, 10, 15),
            "location": "Nordsee, Schleswig-Holstein",
            "project_type": "Construction Supervision",
            "contracting_authority": "RWE Renewables GmbH",
            "participants": [],
            "contact_details": {
                "name": "Ing. Thomas Nordmann",
                "email": "t.nordmann@rwe.com",
                "phone": "+49 201 1234 5678"
            },
            "tender_date": datetime(2025, 7, 25),
            "category": "Construction Supervision",
            "platform_source": "Vergabe.NRW",
            "platform_url": "https://www.evergabe.nrw.de",
            "status": "New",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Change Order Management - Stuttgart 21",
            "description": "Manage and coordinate all change orders for Stuttgart 21 railway project. Documentation, approval workflows, cost tracking.",
            "budget": "€2,100,000",
            "deadline": datetime(2025, 9, 30),
            "location": "Stuttgart, Baden-Württemberg",
            "project_type": "Change Management",
            "contracting_authority": "DB Projekt Stuttgart-Ulm GmbH",
            "participants": [],
            "contact_details": {
                "name": "Dipl.-Ing. Robert Bauer",
                "email": "r.bauer@stuttgart21.de",
                "phone": "+49 711 2092 1234"
            },
            "tender_date": datetime(2025, 7, 28),
            "category": "Change Order Management",
            "platform_source": "Vergabe Baden-Württemberg",
            "platform_url": "https://vergabe.landbw.de",
            "status": "New",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Cost Management & Controlling - Tesla Gigafactory Extension",
            "description": "Comprehensive cost management for Gigafactory Berlin extension. Budget control, variance analysis, forecasting, reporting.",
            "budget": "€3,800,000",
            "deadline": datetime(2025, 10, 20),
            "location": "Grünheide, Brandenburg",
            "project_type": "Cost Management",
            "contracting_authority": "Tesla Manufacturing Brandenburg SE",
            "participants": [],
            "contact_details": {
                "name": "Sarah Müller",
                "email": "s.mueller@tesla.com",
                "phone": "+49 33638 8888"
            },
            "tender_date": datetime(2025, 7, 30),
            "category": "Cost Management",
            "platform_source": "Vergabe Brandenburg",
            "platform_url": "https://vergabe.brandenburg.de",
            "status": "New",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Tendering Process Optimization - BER Airport Phase 2",
            "description": "Optimize and streamline tendering processes for Berlin Brandenburg Airport Phase 2 expansion. Digital workflows, vendor management.",
            "budget": "€1,200,000",
            "deadline": datetime(2025, 9, 15),
            "location": "Schönefeld, Berlin",
            "project_type": "Process Consulting",
            "contracting_authority": "Flughafen Berlin Brandenburg GmbH",
            "participants": [],
            "contact_details": {
                "name": "Frank Lehmann",
                "email": "f.lehmann@berlin-airport.de",
                "phone": "+49 30 6091 1234"
            },
            "tender_date": datetime(2025, 8, 1),
            "category": "Tendering Process",
            "platform_source": "Vergabeplattform Berlin",
            "platform_url": "https://berlin.de/vergabeplattform",
            "status": "New",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Project Completion & Commissioning - BMW Werk Leipzig",
            "description": "Manage final project completion phase for BMW production facility. Systems commissioning, quality checks, final documentation.",
            "budget": "€2,500,000",
            "deadline": datetime(2025, 11, 30),
            "location": "Leipzig, Sachsen",
            "project_type": "Project Completion",
            "contracting_authority": "BMW AG",
            "participants": [],
            "contact_details": {
                "name": "Dr. Martin Koch",
                "email": "m.koch@bmw.de",
                "phone": "+49 341 445 1234"
            },
            "tender_date": datetime(2025, 8, 5),
            "category": "Project Completion",
            "platform_source": "Sachsen Vergabe",
            "platform_url": "https://www.sachsen-vergabe.de",
            "status": "New",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Handover Documentation - Elbphilharmonie Maintenance Center",
            "description": "Complete handover documentation package for Elbphilharmonie maintenance facility. As-built drawings, O&M manuals, warranty documents.",
            "budget": "€680,000",
            "deadline": datetime(2025, 10, 10),
            "location": "Hamburg",
            "project_type": "Documentation Services",
            "contracting_authority": "Freie und Hansestadt Hamburg",
            "participants": [],
            "contact_details": {
                "name": "Petra Schröder",
                "email": "p.schroeder@hamburg.de",
                "phone": "+49 40 428 1234"
            },
            "tender_date": datetime(2025, 8, 8),
            "category": "Handover Documentation",
            "platform_source": "Hamburg Vergabe",
            "platform_url": "https://www.hamburg.de/wirtschaft/ausschreibungen-wirtschaft/",
            "status": "New",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        # Hospital/Klinikum Tenders
        {
            "title": "Neubau Klinikum Jena - Project Management IPA",
            "description": "Integrated project management for new university hospital construction in Jena. 850 beds capacity, state-of-the-art medical facilities with IPA delivery method.",
            "budget": "€12,500,000",
            "deadline": datetime(2025, 10, 15),
            "location": "Jena, Thüringen",
            "project_type": "Hospital Construction",
            "contracting_authority": "Universitätsklinikum Jena",
            "participants": [],
            "contact_details": {
                "name": "Dr. med. Hans Berger",
                "email": "h.berger@med.uni-jena.de",
                "phone": "+49 3641 9320123"
            },
            "tender_date": datetime(2025, 8, 15),
            "category": "IPA",
            "building_typology": "Healthcare",
            "platform_source": "Universitätsklinikum Jena",
            "platform_url": "https://www.uniklinikum-jena.de/Ausschreibungen.html",
            "status": "New",
            "is_applied": False,
            "application_status": "Not Applied",
            "linkedin_connections": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Erweiterungsbau Universitätsklinikum Dresden",
            "description": "Expansion project for Dresden University Hospital. New surgical wing and intensive care unit. Lean construction approach required.",
            "budget": "€8,200,000",
            "deadline": datetime(2025, 11, 1),
            "location": "Dresden, Sachsen",
            "project_type": "Hospital Expansion",
            "contracting_authority": "Universitätsklinikum Dresden",
            "participants": [],
            "contact_details": {
                "name": "Dipl.-Ing. Sabine Richter",
                "email": "s.richter@uniklinikum-dresden.de",
                "phone": "+49 351 458 1234"
            },
            "tender_date": datetime(2025, 8, 20),
            "category": "Lean Management",
            "building_typology": "Healthcare",
            "platform_source": "Universitätsklinikum Dresden",
            "platform_url": "https://www.uniklinikum-dresden.de/de/das-klinikum/universitaetsklinikum-carl-gustav-carus/geschaeftsbereich-logistik-und-einkauf/vergabe",
            "status": "New",
            "is_applied": False,
            "application_status": "Not Applied",
            "linkedin_connections": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Risk Assessment Klinikum Würzburg Modernisierung",
            "description": "Risk management services for Würzburg Hospital modernization project. Assessment of structural, operational and compliance risks.",
            "budget": "€1,800,000",
            "deadline": datetime(2025, 9, 25),
            "location": "Würzburg, Bayern",
            "project_type": "Risk Assessment",
            "contracting_authority": "Universitätsklinikum Würzburg",
            "participants": [],
            "contact_details": {
                "name": "Prof. Dr. Michael Baumann",
                "email": "m.baumann@ukw.de",
                "phone": "+49 931 201 5678"
            },
            "tender_date": datetime(2025, 8, 10),
            "category": "Risk Management",
            "building_typology": "Healthcare",
            "platform_source": "Universitätsklinikum Würzburg",
            "platform_url": "https://www.ukw.de/ausschreibungen/startseite/",
            "status": "New",
            "is_applied": False,
            "application_status": "Not Applied",
            "linkedin_connections": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        # Data Center Tender
        {
            "title": "Data Center Frankfurt - Cost Management",
            "description": "Cost management and controlling for new hyperscale data center in Frankfurt. 100MW facility with redundant systems.",
            "budget": "€4,500,000",
            "deadline": datetime(2025, 10, 30),
            "location": "Frankfurt am Main, Hessen",
            "project_type": "Data Center Construction",
            "contracting_authority": "DE-CIX Data Center GmbH",
            "participants": [],
            "contact_details": {
                "name": "Thomas Weber",
                "email": "t.weber@de-cix.net",
                "phone": "+49 69 1730 9876"
            },
            "tender_date": datetime(2025, 8, 25),
            "category": "Cost Management",
            "building_typology": "Data Center",
            "platform_source": "TED (Tenders Electronic Daily)",
            "platform_url": "https://ted.europa.eu",
            "status": "New",
            "is_applied": False,
            "application_status": "Not Applied",
            "linkedin_connections": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        # Commercial/Mixed-Use
        {
            "title": "Mixed-Use Development Düsseldorf - IPD Delivery",
            "description": "Integrated Project Delivery for mixed-use development in Düsseldorf MedienHafen. Office, retail, and residential components.",
            "budget": "€18,000,000",
            "deadline": datetime(2025, 12, 1),
            "location": "Düsseldorf, NRW",
            "project_type": "Mixed-Use Development",
            "contracting_authority": "Catella Project Management GmbH",
            "participants": [],
            "contact_details": {
                "name": "Anna Schulze",
                "email": "a.schulze@catella.com",
                "phone": "+49 211 8765 4321"
            },
            "tender_date": datetime(2025, 9, 1),
            "category": "IPD",
            "building_typology": "Mixed-Use",
            "platform_source": "e-Vergabe NRW",
            "platform_url": "https://www.evergabe.nrw.de",
            "status": "New",
            "is_applied": False,
            "application_status": "Not Applied",
            "linkedin_connections": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    await db.tenders.insert_many(sample_tenders)
    
    # News articles about stuck/underperforming projects
    news_articles = [
        {
            "title": "Stuttgart 21 Faces Further Delays - Cost Overruns Reach €2.3 Billion",
            "description": "Major railway project experiencing significant delays due to groundwater issues and unexpected geological conditions.",
            "content": "The Stuttgart 21 underground railway station project continues to face challenges with costs now exceeding original estimates by €2.3 billion. Technical difficulties with tunnel boring and groundwater management have caused 18-month delays. Project requires experienced risk management and cost control specialists.",
            "source": "Bauwirtschaft News",
            "url": "https://example.com/news/stuttgart21-delays",
            "project_name": "Stuttgart 21",
            "location": "Stuttgart, Baden-Württemberg",
            "issue_type": "stuck",
            "severity": "high",
            "published_date": datetime(2025, 7, 20),
            "created_at": datetime.utcnow()
        },
        {
            "title": "Berlin Housing Project Behind Schedule - Developer Seeks PM Support",
            "description": "Major residential development in Berlin-Spandau running 6 months behind schedule due to supply chain disruptions.",
            "content": "Gewobag's flagship housing project in Berlin-Spandau is experiencing significant delays. 350-unit development requires immediate project management intervention to recover schedule. Procurement issues and contractor disputes need resolution.",
            "source": "Deutsche Bauzeitung",
            "url": "https://example.com/news/berlin-housing-delays",
            "project_name": "Spandau Wohnquartier",
            "location": "Berlin-Spandau",
            "issue_type": "underperforming",
            "severity": "medium",
            "published_date": datetime(2025, 7, 18),
            "created_at": datetime.utcnow()
        },
        {
            "title": "München Metro Extension Stalled - €850M Project Needs Lean Management",
            "description": "U9 extension project experiencing workflow inefficiencies and coordination problems between contractors.",
            "content": "Munich's U9 subway extension has ground to a halt due to severe coordination issues between multiple contractors. MVG seeks lean management consultants to optimize workflows and get the €850 million project back on track.",
            "source": "Süddeutsche Baujournal",
            "url": "https://example.com/news/munich-metro-stalled",
            "project_name": "U9 Extension München",
            "location": "München, Bayern",
            "issue_type": "stuck",
            "severity": "high",
            "published_date": datetime(2025, 7, 15),
            "created_at": datetime.utcnow()
        },
        {
            "title": "Hospital Construction in Düsseldorf Requires Intervention",
            "description": "University hospital expansion facing quality issues and missing completion milestones.",
            "content": "The €180 million Universitätsklinikum Düsseldorf expansion is experiencing serious quality control issues. Multiple failed inspections and substandard work require immediate construction supervision specialists.",
            "source": "Gesundheitsbau Magazin",
            "url": "https://example.com/news/dusseldorf-hospital",
            "project_name": "Uniklinik Düsseldorf Extension",
            "location": "Düsseldorf, NRW",
            "issue_type": "underperforming",
            "severity": "high",
            "published_date": datetime(2025, 7, 12),
            "created_at": datetime.utcnow()
        },
        {
            "title": "Opportunities in Green Energy Sector - 15 New Wind Parks Announced",
            "description": "German government announces major expansion of renewable energy infrastructure across northern states.",
            "content": "Bundesnetzagentur announces tender opportunities for 15 new offshore and onshore wind parks totaling €4.5 billion investment. Projects require comprehensive project management, risk assessment, and construction supervision services.",
            "source": "Erneuerbare Energien News",
            "url": "https://example.com/news/wind-park-opportunities",
            "project_name": "Wind Energy Expansion 2025",
            "location": "Norddeutschland",
            "issue_type": "opportunity",
            "severity": "low",
            "published_date": datetime(2025, 7, 25),
            "created_at": datetime.utcnow()
        }
    ]
    
    await db.news.insert_many(news_articles)
    
    # Developer projects with timelines
    developer_projects = [
        {
            "developer_name": "HOCHTIEF Development GmbH",
            "developer_url": "https://www.hochtief.de",
            "project_name": "Frankfurt Garden Towers",
            "description": "Twin-tower mixed-use development with residential, office, and retail spaces. 45-story buildings with sustainable design.",
            "location": "Frankfurt am Main, Hessen",
            "budget": "€650,000,000",
            "project_type": "Mixed-Use Development",
            "status": "ongoing",
            "start_date": datetime(2024, 3, 1),
            "expected_completion": datetime(2027, 12, 31),
            "actual_completion": None,
            "timeline_phases": [
                {"phase": "Planning & Permits", "status": "completed", "completion_date": "2024-02-28", "progress": 100},
                {"phase": "Foundation Work", "status": "completed", "completion_date": "2024-09-30", "progress": 100},
                {"phase": "Structural Construction", "status": "ongoing", "completion_date": "2026-06-30", "progress": 45},
                {"phase": "MEP Installation", "status": "pending", "completion_date": "2027-03-31", "progress": 0},
                {"phase": "Interior Fit-out", "status": "pending", "completion_date": "2027-09-30", "progress": 0},
                {"phase": "Commissioning", "status": "pending", "completion_date": "2027-12-31", "progress": 0}
            ],
            "contacts": {
                "project_manager": "Dipl.-Ing. Marcus Weber",
                "email": "m.weber@hochtief.de",
                "phone": "+49 69 8765 4321"
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "developer_name": "ZÜBLIN AG",
            "developer_url": "https://www.zueblin.de",
            "project_name": "München Innovation Hub",
            "description": "State-of-the-art technology and research campus with laboratory facilities, co-working spaces, and startup incubators.",
            "location": "München, Bayern",
            "budget": "€420,000,000",
            "project_type": "Technology Campus",
            "status": "delayed",
            "start_date": datetime(2023, 6, 1),
            "expected_completion": datetime(2026, 6, 30),
            "actual_completion": None,
            "timeline_phases": [
                {"phase": "Site Preparation", "status": "completed", "completion_date": "2023-09-30", "progress": 100},
                {"phase": "Foundation & Basement", "status": "completed", "completion_date": "2024-03-31", "progress": 100},
                {"phase": "Superstructure", "status": "delayed", "completion_date": "2025-09-30", "progress": 60},
                {"phase": "Building Envelope", "status": "pending", "completion_date": "2026-03-31", "progress": 15},
                {"phase": "Technical Systems", "status": "pending", "completion_date": "2026-06-30", "progress": 0}
            ],
            "contacts": {
                "project_manager": "Dr. Anna Schneider",
                "email": "a.schneider@zueblin.de",
                "phone": "+49 89 4567 8901"
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "developer_name": "BAM Deutschland AG",
            "developer_url": "https://www.bam-deutschland.de",
            "project_name": "Hamburg Hafencity Quartier 7",
            "description": "Waterfront residential and commercial development. 800 residential units with ground-floor retail and public spaces.",
            "location": "Hamburg-HafenCity",
            "budget": "€580,000,000",
            "project_type": "Waterfront Development",
            "status": "planning",
            "start_date": datetime(2026, 1, 1),
            "expected_completion": datetime(2029, 12, 31),
            "actual_completion": None,
            "timeline_phases": [
                {"phase": "Master Planning", "status": "ongoing", "completion_date": "2025-12-31", "progress": 75},
                {"phase": "Permits & Approvals", "status": "ongoing", "completion_date": "2025-12-31", "progress": 50},
                {"phase": "Site Works", "status": "pending", "completion_date": "2026-09-30", "progress": 0},
                {"phase": "Phase 1 Construction", "status": "pending", "completion_date": "2028-06-30", "progress": 0},
                {"phase": "Phase 2 Construction", "status": "pending", "completion_date": "2029-12-31", "progress": 0}
            ],
            "contacts": {
                "project_manager": "Ing. Stefan Hoffmann",
                "email": "s.hoffmann@bam.de",
                "phone": "+49 40 1234 5678"
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "developer_name": "STRABAG SE",
            "developer_url": "https://www.strabag.com",
            "project_name": "Berlin Tesla Gigafactory Logistics Center",
            "description": "Large-scale logistics and distribution center supporting Tesla operations. Automated warehouse systems.",
            "location": "Grünheide, Brandenburg",
            "budget": "€280,000,000",
            "project_type": "Industrial/Logistics",
            "status": "ongoing",
            "start_date": datetime(2024, 9, 1),
            "expected_completion": datetime(2026, 3, 31),
            "actual_completion": None,
            "timeline_phases": [
                {"phase": "Site Development", "status": "completed", "completion_date": "2024-12-31", "progress": 100},
                {"phase": "Foundation & Slab", "status": "completed", "completion_date": "2025-03-31", "progress": 100},
                {"phase": "Steel Structure", "status": "ongoing", "completion_date": "2025-09-30", "progress": 70},
                {"phase": "Building Envelope", "status": "ongoing", "completion_date": "2025-12-31", "progress": 30},
                {"phase": "Automation Systems", "status": "pending", "completion_date": "2026-03-31", "progress": 0}
            ],
            "contacts": {
                "project_manager": "Michael Braun",
                "email": "m.braun@strabag.com",
                "phone": "+49 33638 7777"
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "developer_name": "GOLDBECK GmbH",
            "developer_url": "https://www.goldbeck.de",
            "project_name": "Köln Data Center Campus",
            "description": "Hyperscale data center facility with redundant power and cooling systems. 50MW capacity across three buildings.",
            "location": "Köln, Nordrhein-Westfalen",
            "budget": "€390,000,000",
            "project_type": "Data Center",
            "status": "ongoing",
            "start_date": datetime(2024, 1, 1),
            "expected_completion": datetime(2025, 12, 31),
            "actual_completion": None,
            "timeline_phases": [
                {"phase": "Infrastructure", "status": "completed", "completion_date": "2024-06-30", "progress": 100},
                {"phase": "Building Shell", "status": "completed", "completion_date": "2024-12-31", "progress": 100},
                {"phase": "MEP Systems", "status": "ongoing", "completion_date": "2025-09-30", "progress": 65},
                {"phase": "IT Infrastructure", "status": "ongoing", "completion_date": "2025-11-30", "progress": 40},
                {"phase": "Testing & Commissioning", "status": "pending", "completion_date": "2025-12-31", "progress": 0}
            ],
            "contacts": {
                "project_manager": "Julia Fischer",
                "email": "j.fischer@goldbeck.de",
                "phone": "+49 221 9876 5432"
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    await db.developer_projects.insert_many(developer_projects)
    
    tender_count = len(sample_tenders)
    news_count = len(news_articles)
    projects_count = len(developer_projects)
    portals_count = len(sample_portals)
    
    return {
        "message": f"Successfully seeded {tender_count} tenders, {news_count} news articles, {projects_count} developer projects, and {portals_count} tender portals"
    }

# ============ LIVE SCRAPING ENDPOINTS ============

@api_router.post("/scrape/all")
@limiter.limit("1/minute")
async def scrape_all_tenders(
    request: Request,
    max_per_portal: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """
    Scrape live tenders from all available German tender portals.
    Only Directors and Partners can initiate scraping.
    GDPR: Only public tender data is collected.
    """
    if not check_permission(current_user, "scrape"):
        raise HTTPException(
            status_code=403, 
            detail="Only Directors can initiate live scraping"
        )
    
    try:
        from scraper import scrape_all_portals
        
        logger.info(f"Starting live scrape initiated by {current_user['email']}")
        
        # Scrape all portals
        scraped_tenders = await scrape_all_portals(max_per_portal=max_per_portal)
        
        if not scraped_tenders:
            return {"message": "No new tenders found", "count": 0, "duplicates_skipped": 0}
        
        # Deduplicate and insert
        inserted = 0
        duplicates = 0
        
        for tender in scraped_tenders:
            # Check if tender already exists by source_id
            existing = await db.tenders.find_one({"source_id": tender.get("source_id")})
            
            if existing:
                duplicates += 1
                continue
            
            await db.tenders.insert_one(tender)
            inserted += 1
        
        logger.info(f"Scraping complete: {inserted} new tenders, {duplicates} duplicates skipped")
        
        return {
            "message": f"Scraping complete",
            "count": inserted,
            "duplicates_skipped": duplicates,
            "sources": ["Bund.de", "TED Europa", "State Portals"]
        }
        
    except ImportError:
        raise HTTPException(status_code=500, detail="Scraper module not available")
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@api_router.get("/scrape/status")
async def get_scrape_status(current_user: dict = Depends(get_current_user)):
    """Get last scrape status and statistics"""
    # Get latest scraped tender
    latest = await db.tenders.find_one(
        {"scraped_at": {"$exists": True}},
        sort=[("scraped_at", -1)]
    )
    
    # Count scraped vs seeded tenders
    scraped_count = await db.tenders.count_documents({"scraped_at": {"$exists": True}})
    total_count = await db.tenders.count_documents({})
    
    return {
        "total_tenders": total_count,
        "scraped_tenders": scraped_count,
        "seeded_tenders": total_count - scraped_count,
        "last_scrape": latest.get("scraped_at") if latest else None,
        "sources": {
            "bund_de": await db.tenders.count_documents({"platform_source": "Bund.de"}),
            "ted_europa": await db.tenders.count_documents({"platform_source": "TED Europa"}),
            "state_portals": await db.tenders.count_documents({"platform_source": {"$regex": "Vergabe", "$options": "i"}})
        }
    }

# ============ EMPLOYEE CONNECTIONS ENDPOINTS ============

@api_router.get("/employees")
async def get_all_employees(
    department: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all employees in the system for sharing/connections.
    Auto-adds to sharing list when user registers.
    """
    query = {"is_active": True} if await db.users.find_one({"is_active": {"$exists": True}}) else {}
    
    if department:
        query["department"] = department
    
    users = await db.users.find(
        query,
        {"hashed_password": 0}  # Exclude password
    ).to_list(100)
    
    employees = []
    for user in users:
        employees.append({
            "id": str(user["_id"]),
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "role": user.get("role", ""),
            "department": user.get("department"),
            "linkedin_url": user.get("linkedin_url"),
            "profile": user.get("profile", {}),
            "is_online": user.get("last_active") and (datetime.utcnow() - user.get("last_active", datetime.min)).seconds < 300
        })
    
    return employees

@api_router.put("/employees/profile")
async def update_employee_profile(
    profile_data: EmployeeProfile,
    current_user: dict = Depends(get_current_user)
):
    """Update employee's extended profile for connections matching"""
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {
            "profile": profile_data.dict(),
            "updated_at": datetime.utcnow()
        }}
    )
    return {"message": "Profile updated successfully"}

@api_router.get("/tenders/{tender_id}/connections")
async def get_tender_connections(
    tender_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Find employees with relevant experience for a tender.
    Matches based on: location, contracting authority, project type.
    """
    tender = await db.tenders.find_one({"_id": ObjectId(tender_id)})
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    # Get all employees with profiles
    employees = await db.users.find(
        {"profile": {"$exists": True}},
        {"hashed_password": 0}
    ).to_list(100)
    
    connections = []
    tender_location = tender.get("location", "").lower()
    tender_authority = tender.get("contracting_authority", "").lower()
    tender_category = tender.get("category", "").lower()
    
    for emp in employees:
        profile = emp.get("profile", {})
        relevance_score = 0
        reasons = []
        
        # Check location experience
        for region in profile.get("regions_experience", []):
            if region.lower() in tender_location or tender_location in region.lower():
                relevance_score += 30
                reasons.append(f"Experience in {region}")
                break
        
        # Check authority experience
        for authority in profile.get("authorities_experience", []):
            if authority.lower() in tender_authority or tender_authority in authority.lower():
                relevance_score += 40
                reasons.append(f"Worked with {authority}")
                break
        
        # Check expertise match
        for expertise in profile.get("expertise", []):
            if expertise.lower() in tender_category:
                relevance_score += 20
                reasons.append(f"Expertise in {expertise}")
                break
        
        if relevance_score > 0:
            connections.append({
                "employee_id": str(emp["_id"]),
                "name": emp.get("name", ""),
                "email": emp.get("email", ""),
                "role": emp.get("role", ""),
                "department": emp.get("department"),
                "linkedin_url": emp.get("linkedin_url"),
                "relevance_score": relevance_score,
                "reasons": reasons
            })
    
    # Sort by relevance
    connections.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return {
        "tender_id": tender_id,
        "tender_title": tender.get("title", ""),
        "connections": connections[:10]  # Top 10 matches
    }

# ============ SHARING ENDPOINTS ============

class ShareRequest(BaseModel):
    tender_id: str
    recipient_ids: List[str]
    message: Optional[str] = None

@api_router.post("/share/tender")
async def share_tender(
    share_req: ShareRequest,
    current_user: dict = Depends(get_current_user)
):
    """Share a tender with other employees"""
    if not check_permission(current_user, "share"):
        raise HTTPException(status_code=403, detail="You don't have permission to share")
    
    tender = await db.tenders.find_one({"_id": ObjectId(share_req.tender_id)})
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    # Create share records
    shares = []
    for recipient_id in share_req.recipient_ids:
        recipient = await db.users.find_one({"_id": ObjectId(recipient_id)})
        if recipient:
            share = {
                "tender_id": share_req.tender_id,
                "tender_title": tender.get("title", ""),
                "shared_by": str(current_user["_id"]),
                "shared_by_name": current_user.get("name", ""),
                "shared_with": recipient_id,
                "shared_with_email": recipient.get("email", ""),
                "message": sanitize_input(share_req.message) if share_req.message else None,
                "created_at": datetime.utcnow(),
                "is_read": False
            }
            await db.shared_tenders.insert_one(share)
            shares.append(share)
    
    return {
        "message": f"Tender shared with {len(shares)} employees",
        "shares": len(shares)
    }

@api_router.get("/share/inbox")
async def get_shared_inbox(
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """Get tenders shared with the current user"""
    query = {"shared_with": str(current_user["_id"])}
    if unread_only:
        query["is_read"] = False
    
    shares = await db.shared_tenders.find(query).sort("created_at", -1).to_list(100)
    
    result = []
    for share in shares:
        result.append({
            "id": str(share["_id"]),
            "tender_id": share.get("tender_id"),
            "tender_title": share.get("tender_title"),
            "shared_by_name": share.get("shared_by_name"),
            "message": share.get("message"),
            "created_at": share.get("created_at"),
            "is_read": share.get("is_read", False)
        })
    
    return result

@api_router.put("/share/{share_id}/read")
async def mark_share_read(
    share_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a shared tender as read"""
    await db.shared_tenders.update_one(
        {"_id": ObjectId(share_id), "shared_with": str(current_user["_id"])},
        {"$set": {"is_read": True}}
    )
    return {"message": "Marked as read"}

# ============ GDPR/DSGVO COMPLIANCE ENDPOINTS ============

@api_router.get("/gdpr/my-data")
async def export_my_data(current_user: dict = Depends(get_current_user)):
    """
    GDPR Article 20: Right to data portability
    Export all personal data for the user
    """
    user_id = str(current_user["_id"])
    
    # Collect all user data
    user_data = await db.users.find_one(
        {"_id": current_user["_id"]},
        {"hashed_password": 0}
    )
    
    # Get user's favorites
    favorites = await db.favorites.find({"user_id": user_id}).to_list(1000)
    
    # Get user's applications
    applications = await db.tenders.find(
        {"applied_by": user_id}
    ).to_list(1000)
    
    # Get shared tenders
    shared_sent = await db.shared_tenders.find({"shared_by": user_id}).to_list(1000)
    shared_received = await db.shared_tenders.find({"shared_with": user_id}).to_list(1000)
    
    export_data = {
        "export_date": datetime.utcnow().isoformat(),
        "user_info": {
            "email": user_data.get("email"),
            "name": user_data.get("name"),
            "role": user_data.get("role"),
            "department": user_data.get("department"),
            "linkedin_url": user_data.get("linkedin_url"),
            "profile": user_data.get("profile"),
            "created_at": str(user_data.get("created_at")),
            "gdpr_consent_date": str(user_data.get("gdpr_consent_date")) if user_data.get("gdpr_consent_date") else None
        },
        "favorites_count": len(favorites),
        "applications_count": len(applications),
        "shared_tenders_sent": len(shared_sent),
        "shared_tenders_received": len(shared_received)
    }
    
    return export_data

@api_router.delete("/gdpr/delete-account")
async def delete_my_account(
    confirm: bool = Query(..., description="Confirm account deletion"),
    current_user: dict = Depends(get_current_user)
):
    """
    GDPR Article 17: Right to erasure (right to be forgotten)
    Permanently delete user account and all associated data
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Please confirm account deletion by setting confirm=true"
        )
    
    user_id = str(current_user["_id"])
    
    # Delete user's data
    await db.favorites.delete_many({"user_id": user_id})
    await db.shared_tenders.delete_many({"$or": [
        {"shared_by": user_id},
        {"shared_with": user_id}
    ]})
    
    # Remove user from applied_by lists
    await db.tenders.update_many(
        {"applied_by": user_id},
        {"$pull": {"applied_by": user_id}}
    )
    
    # Delete user account
    await db.users.delete_one({"_id": current_user["_id"]})
    
    logger.info(f"GDPR: Account deleted for user {current_user['email']}")
    
    return {
        "message": "Account and all associated data permanently deleted",
        "deleted_at": datetime.utcnow().isoformat()
    }

@api_router.get("/gdpr/privacy-policy")
async def get_privacy_policy():
    """Return the GDPR-compliant privacy policy"""
    return {
        "version": "1.0",
        "last_updated": "2025-01-29",
        "language": "de",
        "company": "GroVELLOWS GmbH",
        "data_controller": "GroVELLOWS GmbH",
        "contact_email": "datenschutz@grovellows.de",
        "policy": {
            "data_collected": [
                "Name und E-Mail-Adresse",
                "Berufliche Informationen (Rolle, Abteilung)",
                "LinkedIn-Profil-URL (optional)",
                "Nutzungsdaten und Präferenzen"
            ],
            "purpose": [
                "Bereitstellung der Ausschreibungs-Tracking-Dienste",
                "Ermöglichung der Zusammenarbeit zwischen Mitarbeitern",
                "Benachrichtigungen über relevante Ausschreibungen"
            ],
            "legal_basis": "Einwilligung (Art. 6 Abs. 1 lit. a DSGVO) und berechtigtes Interesse (Art. 6 Abs. 1 lit. f DSGVO)",
            "data_retention": "Daten werden für die Dauer der Nutzung gespeichert und auf Anfrage gelöscht",
            "your_rights": [
                "Recht auf Auskunft (Art. 15 DSGVO)",
                "Recht auf Berichtigung (Art. 16 DSGVO)",
                "Recht auf Löschung (Art. 17 DSGVO)",
                "Recht auf Datenübertragbarkeit (Art. 20 DSGVO)",
                "Recht auf Widerspruch (Art. 21 DSGVO)"
            ]
        }
    }

# ============ NOTIFICATION ENDPOINTS ============

@api_router.get("/notifications")
async def get_notifications(
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """Get user's notifications (silent - no ringtone)"""
    query = {"user_id": str(current_user["_id"])}
    if unread_only:
        query["is_read"] = False
    
    notifications = await db.notifications.find(query).sort("created_at", -1).to_list(50)
    
    return [{
        "id": str(n["_id"]),
        "type": n.get("type"),
        "title": n.get("title"),
        "message": n.get("message"),
        "tenders": n.get("tenders", []),
        "is_read": n.get("is_read", False),
        "sound": n.get("sound", False),
        "created_at": n.get("created_at")
    } for n in notifications]

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark notification as read"""
    await db.notifications.update_one(
        {"_id": ObjectId(notification_id), "user_id": str(current_user["_id"])},
        {"$set": {"is_read": True}}
    )
    return {"message": "Notification marked as read"}

@api_router.put("/notifications/read-all")
async def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    """Mark all notifications as read"""
    await db.notifications.update_many(
        {"user_id": str(current_user["_id"])},
        {"$set": {"is_read": True}}
    )
    return {"message": "All notifications marked as read"}

@api_router.get("/notifications/count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    """Get unread notification count"""
    count = await db.notifications.count_documents({
        "user_id": str(current_user["_id"]),
        "is_read": False
    })
    return {"unread_count": count}

# ============ SCRAPE SETTINGS ============

@api_router.get("/scrape/settings")
async def get_scrape_settings(current_user: dict = Depends(get_current_user)):
    """Get auto-scrape settings"""
    settings = await db.scrape_settings.find_one({}) or {
        "auto_scrape_enabled": True,
        "interval_minutes": 1,
        "last_scrape": None,
        "total_scraped": 0
    }
    return {
        "auto_scrape_enabled": settings.get("auto_scrape_enabled", True),
        "interval_minutes": settings.get("interval_minutes", 1),
        "last_scrape": settings.get("last_scrape"),
        "total_scraped": settings.get("total_scraped", 0)
    }

@api_router.put("/scrape/settings")
async def update_scrape_settings(
    enabled: bool = True,
    interval_minutes: int = 1,
    current_user: dict = Depends(get_current_user)
):
    """Update auto-scrape settings (Directors only)"""
    if not check_permission(current_user, "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    await db.scrape_settings.update_one(
        {},
        {"$set": {
            "auto_scrape_enabled": enabled,
            "interval_minutes": max(1, min(60, interval_minutes)),
            "updated_at": datetime.utcnow()
        }},
        upsert=True
    )
    
    return {"message": f"Auto-scrape {'enabled' if enabled else 'disabled'}, interval: {interval_minutes} min"}

# Include router

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ BACKGROUND TASKS ============

async def auto_scrape_tenders():
    """
    Background task that runs every minute to scrape new tenders.
    Creates notifications for new tenders found.
    """
    try:
        from scraper import scrape_all_portals
        
        logger.info("🔄 Auto-scrape tenders started...")
        
        # Get existing source_ids to detect new tenders
        existing_ids = set()
        async for tender in db.tenders.find({}, {"source_id": 1}):
            if tender.get("source_id"):
                existing_ids.add(tender["source_id"])
        
        # Scrape all portals
        scraped_tenders = await scrape_all_portals(max_per_portal=30)
        
        new_count = 0
        new_tenders = []
        
        for tender in scraped_tenders:
            source_id = tender.get("source_id", "")
            if source_id and source_id not in existing_ids:
                await db.tenders.insert_one(tender)
                new_count += 1
                new_tenders.append(tender)
                existing_ids.add(source_id)
        
        # Create notifications for all users about new tenders
        if new_count > 0:
            users = await db.users.find({"notification_preferences.new_tenders": True}).to_list(1000)
            
            for user in users:
                notification = {
                    "user_id": str(user["_id"]),
                    "type": "new_tenders",
                    "title": f"🆕 {new_count} neue Ausschreibungen gefunden",
                    "message": f"{new_count} neue Ausschreibungen wurden automatisch hinzugefügt.",
                    "tenders": [{"id": str(t.get("_id", "")), "title": t.get("title", "")[:50]} for t in new_tenders[:5]],
                    "is_read": False,
                    "sound": False,  # Silent notification
                    "created_at": datetime.utcnow()
                }
                await db.notifications.insert_one(notification)
            
            logger.info(f"✅ Auto-scrape tenders complete: {new_count} new tenders, {len(users)} users notified")
        else:
            logger.info("✅ Auto-scrape tenders complete: No new tenders found")
            
    except Exception as e:
        logger.error(f"❌ Auto-scrape tenders error: {e}")

async def auto_scrape_news():
    """
    Background task that runs every 5 minutes to scrape construction news.
    Creates notifications for important news found.
    """
    try:
        from news_scraper import scrape_all_news
        
        logger.info("📰 Auto-scrape news started...")
        
        # Get existing source_ids to detect new news
        existing_ids = set()
        async for article in db.news_articles.find({}, {"source_id": 1}):
            if article.get("source_id"):
                existing_ids.add(article["source_id"])
        
        # Scrape all news sources
        scraped_news = await scrape_all_news(max_per_source=15)
        
        new_count = 0
        new_articles = []
        high_relevance_articles = []
        
        for article in scraped_news:
            source_id = article.get("source_id", "")
            if source_id and source_id not in existing_ids:
                await db.news_articles.insert_one(article)
                new_count += 1
                new_articles.append(article)
                existing_ids.add(source_id)
                
                # Track high relevance articles (stuck projects, major news)
                if article.get("relevance_score", 0) >= 80:
                    high_relevance_articles.append(article)
        
        # Create notifications for high-relevance news
        if high_relevance_articles:
            users = await db.users.find({}).to_list(1000)
            
            for user in users:
                notification = {
                    "user_id": str(user["_id"]),
                    "type": "important_news",
                    "title": f"📰 {len(high_relevance_articles)} wichtige Baunachrichten",
                    "message": "Neue relevante Nachrichten aus der Baubranche gefunden.",
                    "articles": [{"title": a.get("title", "")[:50], "source": a.get("source", "")} for a in high_relevance_articles[:3]],
                    "is_read": False,
                    "sound": False,  # Silent notification
                    "created_at": datetime.utcnow()
                }
                await db.notifications.insert_one(notification)
        
        logger.info(f"✅ Auto-scrape news complete: {new_count} new articles, {len(high_relevance_articles)} high relevance")
            
    except Exception as e:
        logger.error(f"❌ Auto-scrape news error: {e}")

async def cleanup_awarded_tenders():
    """
    Background task that runs every 5 minutes to clean up awarded/closed tenders.
    Only removes tenders that are NOT in any user's favorites.
    """
    try:
        logger.info("🧹 Cleanup task started...")
        
        # Get all favorite tender IDs
        favorite_tender_ids = set()
        async for fav in db.favorites.find({}, {"tender_id": 1}):
            favorite_tender_ids.add(fav.get("tender_id"))
        
        # Find awarded/closed tenders that are NOT favorited
        # Status: Closed OR application_status: Won/Lost
        query = {
            "$or": [
                {"status": "Closed"},
                {"application_status": {"$in": ["Won", "Lost"]}},
                {"deadline": {"$lt": datetime.utcnow() - timedelta(days=7)}}  # Expired > 7 days
            ]
        }
        
        deleted_count = 0
        async for tender in db.tenders.find(query):
            tender_id = str(tender["_id"])
            
            # Skip if in anyone's favorites
            if tender_id in favorite_tender_ids:
                continue
            
            # Skip if user has applied to it
            if tender.get("applied_by") and len(tender.get("applied_by", [])) > 0:
                continue
            
            # Delete the tender
            await db.tenders.delete_one({"_id": tender["_id"]})
            deleted_count += 1
        
        if deleted_count > 0:
            logger.info(f"🧹 Cleanup complete: {deleted_count} awarded/expired tenders removed")
        else:
            logger.info("🧹 Cleanup complete: No tenders to remove")
            
    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}")

# ============ APP LIFECYCLE EVENTS ============

@app.on_event("startup")
async def startup_event():
    """Initialize background tasks on startup"""
    logger.info("🚀 Starting GroVELLOWS API Server...")
    
    # Create indexes for better performance
    await db.tenders.create_index("source_id", unique=True, sparse=True)
    await db.tenders.create_index("status")
    await db.tenders.create_index("deadline")
    await db.news_articles.create_index("source_id", unique=True, sparse=True)
    await db.notifications.create_index([("user_id", 1), ("is_read", 1)])
    await db.favorites.create_index([("user_id", 1), ("tender_id", 1)], unique=True)
    
    # Start background scheduler
    scheduler.add_job(
        auto_scrape_tenders,
        IntervalTrigger(minutes=1),
        id="auto_scrape_tenders",
        name="Auto-scrape tenders every minute",
        replace_existing=True
    )
    
    scheduler.add_job(
        auto_scrape_news,
        IntervalTrigger(minutes=5),
        id="auto_scrape_news",
        name="Auto-scrape news every 5 minutes",
        replace_existing=True
    )
    
    scheduler.add_job(
        cleanup_awarded_tenders,
        IntervalTrigger(minutes=5),
        id="cleanup_tenders",
        name="Cleanup awarded tenders every 5 minutes",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("✅ Background scheduler started - Auto-scraping every 1 minute")

@app.on_event("shutdown")
async def shutdown_db_client():
    """Cleanup on shutdown"""
    scheduler.shutdown()
    client.close()
    logger.info("👋 GroVELLOWS API Server shutdown complete")
