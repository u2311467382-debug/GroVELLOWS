from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta
from bson import ObjectId
import jwt
import bcrypt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ MODELS ============

class UserRole(str):
    PROJECT_MANAGER = "Project Manager"
    SENIOR_PROJECT_MANAGER = "Senior Project Manager"
    INTERN = "Intern"
    HR = "HR"
    PARTNER = "Partner"
    DIRECTOR = "Director"

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str
    linkedin_url: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: str
    linkedin_url: Optional[str] = None
    notification_preferences: dict = Field(default_factory=lambda: {
        "new_tenders": True,
        "status_changes": True,
        "ipa_tenders": True,
        "project_management": True,
        "daily_digest": True
    })
    gdpr_consent: Optional[dict] = None
    gdpr_consent_date: Optional[datetime] = None
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
    platform_source: str
    platform_url: str
    status: str = TenderStatus.NEW
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
    current_user: dict = Depends(get_current_user)
):
    query = {}
    
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
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
    share_data: Share,
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
    """Seed comprehensive sample data including tenders, news, and developer projects"""
    
    # Clear existing data for fresh seed
    await db.tenders.delete_many({})
    await db.news.delete_many({})
    await db.developer_projects.delete_many({})
    
    # Existing tenders plus new specialized categories
    sample_tenders = [
        # Original tenders...
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
            "platform_source": "Vergabeplattform Berlin",
            "platform_url": "https://berlin.de/vergabeplattform",
            "status": "New",
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
            "platform_source": "Vergabe Bayern",
            "platform_url": "https://www.vergabe.bayern.de",
            "status": "New",
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
    
    return {
        "message": f"Successfully seeded {tender_count} tenders, {news_count} news articles, and {projects_count} developer projects"
    }

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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
