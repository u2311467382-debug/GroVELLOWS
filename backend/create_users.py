"""
Script to create new users and update sharing permissions
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import bcrypt
from datetime import datetime

load_dotenv()

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

async def update_users():
    print("Starting user updates...")
    
    # 1. Create Jürgen Marc Volm - Partner with sharing rights
    jurgen_email = "jurgen.volm@grovellows.de"
    existing = await db.users.find_one({"email": jurgen_email})
    if existing:
        print(f"User {jurgen_email} already exists - updating...")
        await db.users.update_one(
            {"email": jurgen_email},
            {"$set": {"can_share": True, "role": "Partner"}}
        )
    else:
        await db.users.insert_one({
            "email": jurgen_email,
            "password": hash_password("Jurgen123"),
            "name": "Jürgen Marc Volm",
            "role": "Partner",
            "can_share": True,  # Individual sharing permission
            "mfa_enabled": False,
            "notification_preferences": {
                "new_tenders": True,
                "status_changes": True,
                "ipa_tenders": True,
                "project_management": True,
                "daily_digest": True
            },
            "created_at": datetime.utcnow()
        })
        print(f"✓ Created user: Jürgen Marc Volm ({jurgen_email}) - Role: Partner")
    
    # 2. Create Phillip Kanthack - Project Manager with sharing rights
    phillip_email = "phillip.kanthack@grovellows.de"
    existing = await db.users.find_one({"email": phillip_email})
    if existing:
        print(f"User {phillip_email} already exists - updating...")
        await db.users.update_one(
            {"email": phillip_email},
            {"$set": {"can_share": True, "role": "Project Manager"}}
        )
    else:
        await db.users.insert_one({
            "email": phillip_email,
            "password": hash_password("Phillip123"),
            "name": "Phillip Kanthack",
            "role": "Project Manager",
            "can_share": True,  # Individual sharing permission
            "mfa_enabled": False,
            "notification_preferences": {
                "new_tenders": True,
                "status_changes": True,
                "ipa_tenders": True,
                "project_management": True,
                "daily_digest": True
            },
            "created_at": datetime.utcnow()
        })
        print(f"✓ Created user: Phillip Kanthack ({phillip_email}) - Role: Project Manager with Sharing Rights")
    
    # 3. Update Parth Sheth to have sharing rights
    parth_email = "parth.sheth@grovellows.de"
    result = await db.users.update_one(
        {"email": parth_email},
        {"$set": {"can_share": True}}
    )
    if result.modified_count > 0:
        print(f"✓ Updated Parth Sheth with sharing rights")
    else:
        print(f"Parth Sheth not found or already has sharing rights")
    
    # 4. Make sure other Project Managers don't have sharing rights
    await db.users.update_many(
        {
            "role": "Project Manager",
            "email": {"$nin": [phillip_email, parth_email]}
        },
        {"$set": {"can_share": False}}
    )
    print("✓ Ensured other Project Managers don't have sharing rights")
    
    # 5. List all users for verification
    print("\n--- All Users in Database ---")
    async for user in db.users.find():
        can_share = user.get('can_share', False)
        share_status = "✓ Can Share" if can_share or user.get('role') in ['Director', 'Partner'] else "✗ No Share"
        print(f"  • {user.get('name', 'N/A'):25} | {user.get('email', 'N/A'):35} | {user.get('role', 'N/A'):20} | {share_status}")
    
    print("\n✓ User database update complete!")

if __name__ == "__main__":
    asyncio.run(update_users())
