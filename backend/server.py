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

# ============ SEED DATA ============

@api_router.post("/seed-data")
async def seed_sample_data():
    """Seed sample tender data for testing"""
    
    # Check if data already exists
    count = await db.tenders.count_documents({})
    if count > 0:
        return {"message": "Data already exists"}
    
    sample_tenders = [
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
            "category": TenderCategory.IPA,
            "platform_source": "Vergabeplattform Berlin",
            "platform_url": "https://berlin.de/vergabeplattform",
            "status": TenderStatus.NEW,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Modernisierung Autobahnbrücke A3 Frankfurt",
            "description": "Renovation and modernization of highway bridge on A3 near Frankfurt. Integrated Project Delivery approach required.",
            "budget": "€12,500,000",
            "deadline": datetime(2025, 8, 30),
            "location": "Frankfurt am Main, Hessen",
            "project_type": "Infrastructure - Bridge",
            "contracting_authority": "Autobahn GmbH des Bundes",
            "participants": ["Strabag AG", "Implenia Deutschland"],
            "contact_details": {
                "name": "Ing. Thomas Weber",
                "email": "t.weber@autobahn.de",
                "phone": "+49 69 7890 1234"
            },
            "tender_date": datetime(2025, 6, 28),
            "category": TenderCategory.IPD,
            "platform_source": "Bund.de",
            "platform_url": "https://service.bund.de",
            "status": TenderStatus.NEW,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Neubau Gewerbepark München-Nord",
            "description": "Development of commercial park with office buildings, logistics center and retail spaces. Total area 50,000 sqm.",
            "budget": "€78,000,000",
            "deadline": datetime(2025, 10, 20),
            "location": "München, Bayern",
            "project_type": "Commercial Construction",
            "contracting_authority": "Stadt München - Referat für Wirtschaft",
            "participants": ["Bilfinger SE", "Max Bögl", "Leonhard Weiss"],
            "contact_details": {
                "name": "Anna Schmidt",
                "email": "a.schmidt@muenchen.de",
                "phone": "+49 89 2345 6789"
            },
            "tender_date": datetime(2025, 7, 5),
            "category": TenderCategory.PROJECT_MANAGEMENT,
            "platform_source": "Vergabe Bayern",
            "platform_url": "https://www.vergabe.bayern.de",
            "status": TenderStatus.NEW,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Sanierung Schulkomplex Hamburg-Altona",
            "description": "Complete renovation of school complex including 3 buildings, sports facilities, and energy efficiency upgrades.",
            "budget": "€23,000,000",
            "deadline": datetime(2025, 8, 15),
            "location": "Hamburg-Altona, Hamburg",
            "project_type": "Public Building Renovation",
            "contracting_authority": "Schulbau Hamburg",
            "participants": ["Goldbeck GmbH", "Ed. Züblin AG"],
            "contact_details": {
                "name": "Michael Becker",
                "email": "m.becker@schulbau.hamburg.de",
                "phone": "+49 40 4567 8901"
            },
            "tender_date": datetime(2025, 6, 25),
            "category": TenderCategory.INTEGRATED_PM,
            "platform_source": "Hamburg Vergabe",
            "platform_url": "https://www.hamburg.de/wirtschaft/ausschreibungen-wirtschaft/",
            "status": TenderStatus.NEW,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Bau Klinikum Erweiterung Stuttgart",
            "description": "Extension of hospital with new surgical wing, emergency department and parking structure. High-tech medical facility.",
            "budget": "€95,000,000",
            "deadline": datetime(2025, 11, 30),
            "location": "Stuttgart, Baden-Württemberg",
            "project_type": "Healthcare Construction",
            "contracting_authority": "Klinikum Stuttgart",
            "participants": ["Wolff & Müller", "Züblin AG", "Baresel"],
            "contact_details": {
                "name": "Dr. Sabine Fischer",
                "email": "s.fischer@klinikum-stuttgart.de",
                "phone": "+49 711 8901 2345"
            },
            "tender_date": datetime(2025, 7, 10),
            "category": TenderCategory.IPA,
            "platform_source": "Vergabe Baden-Württemberg",
            "platform_url": "https://vergabe.landbw.de",
            "status": TenderStatus.NEW,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Hochwasserschutz Rheinufer Köln",
            "description": "Construction of flood protection measures along Rhine riverbank, including dikes, walls and pump stations.",
            "budget": "€32,000,000",
            "deadline": datetime(2025, 9, 30),
            "location": "Köln, Nordrhein-Westfalen",
            "project_type": "Water Management Infrastructure",
            "contracting_authority": "Stadt Köln - Umweltamt",
            "participants": ["Strabag AG", "Hochtief AG"],
            "contact_details": {
                "name": "Dipl.-Ing. Peter Hartmann",
                "email": "p.hartmann@stadt-koeln.de",
                "phone": "+49 221 3456 7890"
            },
            "tender_date": datetime(2025, 6, 30),
            "category": TenderCategory.PROJECT_MANAGEMENT,
            "platform_source": "e-Vergabe NRW",
            "platform_url": "https://www.evergabe.nrw.de",
            "status": TenderStatus.NEW,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Neubau Technologiepark Dresden",
            "description": "Development of technology park for research and development, including laboratory buildings and clean rooms.",
            "budget": "€65,000,000",
            "deadline": datetime(2025, 10, 15),
            "location": "Dresden, Sachsen",
            "project_type": "Research & Technology",
            "contracting_authority": "Technische Universität Dresden",
            "participants": ["Porr Deutschland", "Max Bögl", "Implenia"],
            "contact_details": {
                "name": "Prof. Dr. Martin Schneider",
                "email": "m.schneider@tu-dresden.de",
                "phone": "+49 351 4567 8901"
            },
            "tender_date": datetime(2025, 7, 8),
            "category": TenderCategory.IPD,
            "platform_source": "Sachsen Vergabe",
            "platform_url": "https://www.sachsen-vergabe.de",
            "status": TenderStatus.NEW,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Ausbau U-Bahn Linie U5 Berlin",
            "description": "Extension of subway line U5 with 3 new stations, tunnels and technical infrastructure. Urban transit project.",
            "budget": "€180,000,000",
            "deadline": datetime(2025, 12, 31),
            "location": "Berlin",
            "project_type": "Public Transportation",
            "contracting_authority": "Berliner Verkehrsbetriebe (BVG)",
            "participants": ["Hochtief AG", "Strabag AG", "Züblin AG", "Bilfinger SE"],
            "contact_details": {
                "name": "Dipl.-Ing. Andreas Hoffmann",
                "email": "a.hoffmann@bvg.de",
                "phone": "+49 30 5678 9012"
            },
            "tender_date": datetime(2025, 7, 12),
            "category": TenderCategory.IPA,
            "platform_source": "Vergabeplattform Berlin",
            "platform_url": "https://berlin.de/vergabeplattform",
            "status": TenderStatus.NEW,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    await db.tenders.insert_many(sample_tenders)
    
    return {"message": f"Successfully seeded {len(sample_tenders)} sample tenders"}

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
