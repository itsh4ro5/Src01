from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_DB, DB_NAME

client = AsyncIOMotorClient(MONGO_DB)
db = client[DB_NAME]
users_collection = db["users"] # Aapki user collection ka naam

async def save_user_cookie(user_id, platform, cookie_text):
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {f"cookies.{platform}": cookie_text}},
        upsert=True
    )

async def get_user_cookie(user_id, platform):
    user = await users_collection.find_one({"_id": user_id})
    if user and "cookies" in user and platform in user["cookies"]:
        return user["cookies"][platform]
    return None