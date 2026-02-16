"""
Script to update users in the database:
1. Update director name from "Max director" to "Lorenz Walter"
2. Create 3 new test users with specific roles
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
    print("Starting user database update...")
    
    # 1. Update director name from "Max director" to "Lorenz Walter"
    result = await db.users.update_one(
        {"email": "director@grovellows.de"},
        {"$set": {"name": "Lorenz Walter"}}
    )
    if result.modified_count > 0:
        print("✓ Updated director name to 'Lorenz Walter'")
    else:
        # Check if user exists
        director = await db.users.find_one({"email": "director@grovellows.de"})
        if director:
            print(f"Director found with name: {director.get('name')} - no update needed or name already correct")
        else:
            print("Director user not found, creating...")
            await db.users.insert_one({
                "email": "director@grovellows.de",
                "password": hash_password("Director123"),
                "name": "Lorenz Walter",
                "role": "Director",
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
            print("✓ Created director user 'Lorenz Walter'")
    
    # 2. Create new test users
    new_users = [
        {
            "email": "stephan.hintzen@grovellows.de",
            "password": hash_password("Stephan123"),
            "name": "Stephan Hintzen",
            "role": "Partner",
            "mfa_enabled": False,
            "notification_preferences": {
                "new_tenders": True,
                "status_changes": True,
                "ipa_tenders": True,
                "project_management": True,
                "daily_digest": True
            },
            "created_at": datetime.utcnow()
        },
        {
            "email": "vesna.udovcic@grovellows.de",
            "password": hash_password("Vesna123"),
            "name": "Vesna Udovcic",
            "role": "Admin",  # Note: Role permissions may need to be checked if "Admin" is supported
            "mfa_enabled": False,
            "notification_preferences": {
                "new_tenders": True,
                "status_changes": True,
                "ipa_tenders": True,
                "project_management": True,
                "daily_digest": True
            },
            "created_at": datetime.utcnow()
        },
        {
            "email": "parth.sheth@grovellows.de",
            "password": hash_password("Parth123"),
            "name": "Parth Sheth",
            "role": "Project Manager",
            "mfa_enabled": False,
            "notification_preferences": {
                "new_tenders": True,
                "status_changes": True,
                "ipa_tenders": True,
                "project_management": True,
                "daily_digest": True
            },
            "created_at": datetime.utcnow()
        }
    ]
    
    for user in new_users:
        # Check if user already exists
        existing = await db.users.find_one({"email": user["email"]})
        if existing:
            print(f"User {user['email']} already exists - skipping")
        else:
            await db.users.insert_one(user)
            print(f"✓ Created user: {user['name']} ({user['email']}) - Role: {user['role']}")
    
    # 3. List all users for verification
    print("\n--- All Users in Database ---")
    async for user in db.users.find():
        print(f"  • {user.get('name', 'N/A')} ({user.get('email', 'N/A')}) - Role: {user.get('role', 'N/A')}")
    
    print("\n✓ User database update complete!")

if __name__ == "__main__":
    asyncio.run(update_users())
