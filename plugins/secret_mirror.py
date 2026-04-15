asimport os
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import ChatPrivileges
from motor.motor_asyncio import AsyncIOMotorClient
from config import API_ID, API_HASH, OWNER_ID
from shared_client import app as MAIN_BOT

logger = logging.getLogger(__name__)

# Global Variables
SECRET_DB = None
mirror_col = None
config_col = None

SECRET_USER = None
SECRET_BOT = None

# 🟢 Initialize Secret MongoDB
async def init_secret_db():
    global SECRET_DB, mirror_col, config_col
    secret_url = os.getenv("SECRET_MONGO_DB", "")
    if secret_url:
        try:
            client = AsyncIOMotorClient(secret_url)
            SECRET_DB = client["Secret_Archive_System"]
            mirror_col = SECRET_DB["channel_maps"]
            config_col = SECRET_DB["config"]
            logger.info("✅ Secret Backup MongoDB Connected!")
        except Exception as e:
            logger.warning(f"⚠️ Secret DB Error: {e}")

# 🟢 Start Secret Clients securely
async def start_secret_clients():
    global SECRET_USER, SECRET_BOT
    if config_col is None: return False

    config = await config_col.find_one({"_id": "secret_credentials"})
    if not config: return False

    try:
        if not SECRET_USER or not SECRET_USER.is_connected:
            SECRET_USER = Client("secret_user", session_string=config.get("session_string"), api_id=API_ID, api_hash=API_HASH)
            await SECRET_USER.start()
        
        if not SECRET_BOT or not SECRET_BOT.is_connected:
            SECRET_BOT = Client("secret_bot", bot_token=config.get("bot_token"), api_id=API_ID, api_hash=API_HASH)
            await SECRET_BOT.start()
            
        return True
    except Exception as e:
        logger.error(f"⚠️ Failed to start secret clients: {e}")
        return False

# 🟢 Main Backup Engine (Runs in background secretly)
async def perform_secret_mirror(source_chat_id, source_chat_title, log_msg_id, log_group_id):
    if not await start_secret_clients():
        return 

    try:
        mapping = await mirror_col.find_one({"source_id": str(source_chat_id)})
        
        if not mapping:
            safe_title = f"{source_chat_title[:100]} [Backup]" if source_chat_title else f"Unknown_Backup_{source_chat_id}"
            new_chat = await SECRET_USER.create_channel(title=safe_title)
            
            secret_bot_info = await SECRET_BOT.get_me()
            bot_username = secret_bot_info.username
            
            await asyncio.sleep(2) 
            await SECRET_USER.add_chat_members(new_chat.id, bot_username)
            await SECRET_USER.promote_chat_member(
                new_chat.id, 
                bot_username, 
                privileges=ChatPrivileges(can_post_messages=True, can_edit_messages=True, can_delete_messages=True)
            )
            
            mapping = {"source_id": str(source_chat_id), "secret_chat_id": new_chat.id}
            await mirror_col.insert_one(mapping)
        
        secret_chat_id = mapping["secret_chat_id"]

        await asyncio.sleep(1) 
        await SECRET_BOT.copy_message(
            chat_id=secret_chat_id,
            from_chat_id=log_group_id,
            message_id=log_msg_id
        )
        
    except Exception as e:
        logger.error(f"⚠️ Secret Mirror Error: {e}")

# ==========================================
# 🛠️ OWNER COMMANDS TO SETUP FROM TELEGRAM
# ==========================================

@MAIN_BOT.on_message(filters.command("setsecretsession") & filters.user(OWNER_ID))
async def set_secret_session(c, m):
    if len(m.command) < 2:
        return await m.reply("❌ Send session string too: `/setsecretsession string...`")
    
    await init_secret_db()
    if config_col is not None:
        await config_col.update_one({"_id": "secret_credentials"}, {"$set": {"session_string": m.command[1]}}, upsert=True)
        await m.reply("✅ Secret User Session Saved!")

@MAIN_BOT.on_message(filters.command("setsecretbot") & filters.user(OWNER_ID))
async def set_secret_bot(c, m):
    if len(m.command) < 2:
        return await m.reply("❌ Send bot token too: `/setsecretbot 1234:ABC...`")
    
    await init_secret_db()
    if config_col is not None:
        await config_col.update_one({"_id": "secret_credentials"}, {"$set": {"bot_token": m.command[1]}}, upsert=True)
        await m.reply("✅ Secret Bot Token Saved!")

asyncio.get_event_loop().create_task(init_secret_db())