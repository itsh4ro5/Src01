import os
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import ChatPrivileges
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired, BadRequest
from motor.motor_asyncio import AsyncIOMotorClient
from config import API_ID, API_HASH, OWNER_ID
from shared_client import app as MAIN_BOT

logger = logging.getLogger(__name__)

# GLOBAL VARIABLES
SECRET_DB = None
mirror_col = None
config_col = None
SECRET_USER = None
SECRET_BOT = None

# ==========================================
# 🟢 1. ROBUST DATABASE INITIALIZATION
# ==========================================

async def init_secret_db():
    global SECRET_DB, mirror_col, config_col
    secret_url = os.getenv("SECRET_MONGO_DB", "")
    if not secret_url:
        logger.warning("⚠️ SECRET_MONGO_DB environment variable is NOT set!")
        return False

    try:
        client = AsyncIOMotorClient(secret_url)
        SECRET_DB = client["Secret_Archive_System"]
        mirror_col = SECRET_DB["channel_maps"]
        config_col = SECRET_DB["config"]
        logger.info("✅ Secret Backup MongoDB Connected Successfully!")
        return True
    except Exception as e:
        logger.error(f"⚠️ Secret DB Connection Error: {e}")
        return False

async def start_secret_clients():
    global SECRET_USER, SECRET_BOT

    if config_col is None:
        logger.info("🔄 Initializing Secret DB dynamically...")
        db_connected = await init_secret_db()
        if not db_connected:
            logger.error("❌ Abort: Database not connected.")
            return False

    config = await config_col.find_one({"_id": "secret_credentials"})
    if not config:
        logger.error("❌ Abort: Credentials not found in DB! Please run /secretlogin and /setsecretbot.")
        return False

    sess_str = config.get("session_string")
    b_token = config.get("bot_token")

    if not sess_str or not b_token:
        logger.error(f"❌ Abort: Missing credentials!")
        return False

    try:
        if not SECRET_USER or not SECRET_USER.is_connected:
            logger.info("🔄 Starting Secret User Client...")
            SECRET_USER = Client("secret_user", session_string=sess_str, api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await SECRET_USER.start()
            logger.info("✅ Secret User Started Successfully!")
        
        if not SECRET_BOT or not SECRET_BOT.is_connected:
            logger.info("🔄 Starting Secret Bot Client...")
            SECRET_BOT = Client("secret_bot", bot_token=b_token, api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await SECRET_BOT.start()
            logger.info("✅ Secret Bot Started Successfully!")
            
        return True
    except Exception as e:
        logger.error(f"⚠️ Failed to start secret clients: {e}")
        return False

# ==========================================
# 🟢 2. AUTO-LOGIN SYSTEM FOR SECRET ACCOUNT
# ==========================================

secret_auth_state = {}
secret_login_cache = {}

def is_secret_login(_, __, message):
    return bool(message.from_user and message.from_user.id in secret_auth_state)

secret_login_filter = filters.create(is_secret_login)

@MAIN_BOT.on_message(filters.command("secretlogin") & filters.user(OWNER_ID))
async def secret_login_cmd(client, message):
    uid = message.from_user.id
    secret_auth_state[uid] = "phone"
    secret_login_cache[uid] = {}
    await message.reply("🕵️ **Secret Backup Account Login**\nSend phone number with country code (e.g. +91...):")

@MAIN_BOT.on_message(filters.command("cancel_secret") & filters.user(OWNER_ID))
async def cancel_secret_cmd(client, message):
    uid = message.from_user.id
    if uid in secret_auth_state:
        del secret_auth_state[uid]
        if uid in secret_login_cache and "temp_client" in secret_login_cache[uid]:
            await secret_login_cache[uid]["temp_client"].disconnect()
        del secret_login_cache[uid]
        await message.reply("✅ Secret login process cancelled.")

@MAIN_BOT.on_message(secret_login_filter & filters.text & filters.private & filters.user(OWNER_ID))
async def handle_secret_login_steps(client, message):
    uid = message.from_user.id
    text = message.text.strip()
    step = secret_auth_state.get(uid)
    if text == "/cancel_secret": return
    msg = await message.reply("🔄 Processing...")

    try:
        if step == "phone":
            temp_client = Client(f"secret_temp_{uid}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await temp_client.connect()
            sent_code = await temp_client.send_code(text)
            secret_login_cache[uid]['phone'] = text
            secret_login_cache[uid]['phone_code_hash'] = sent_code.phone_code_hash
            secret_login_cache[uid]['temp_client'] = temp_client
            secret_auth_state[uid] = "code"
            await msg.edit("✅ Verification code sent!\nEnter code with spaces (e.g. 1 2 3 4 5):")

        elif step == "code":
            code = text.replace(" ", "")
            temp_client = secret_login_cache[uid]['temp_client']
            phone = secret_login_cache[uid]['phone']
            phone_code_hash = secret_login_cache[uid]['phone_code_hash']
            try:
                await temp_client.sign_in(phone, phone_code_hash, code)
                session_string = await temp_client.export_session_string()
                await init_secret_db()
                if config_col is not None:
                    await config_col.update_one({"_id": "secret_credentials"}, {"$set": {"session_string": session_string}}, upsert=True)
                    await msg.edit("🎉 **Success!** Secret session saved.")
                await temp_client.disconnect()
                del secret_auth_state[uid]
                del secret_login_cache[uid]
            except SessionPasswordNeeded:
                secret_auth_state[uid] = "password"
                await msg.edit("🔒 Two-Step Verification is enabled. Send password:")

        elif step == "password":
            temp_client = secret_login_cache[uid]['temp_client']
            await temp_client.check_password(text)
            session_string = await temp_client.export_session_string()
            await init_secret_db()
            if config_col is not None:
                await config_col.update_one({"_id": "secret_credentials"}, {"$set": {"session_string": session_string}}, upsert=True)
                await msg.edit("🎉 **Success!** Secret session saved.")
            await temp_client.disconnect()
            del secret_auth_state[uid]
            del secret_login_cache[uid]
                
    except Exception as e:
        await msg.edit(f"❌ Error: {e}\nPlease try again with /secretlogin")
        secret_auth_state.pop(uid, None)

# ==========================================
# 🟢 3. MAIN MIRRORING ENGINE (FIXED BOT PROMOTION)
# ==========================================

async def perform_secret_mirror(source_chat_id, source_chat_title, log_msg_id, log_group_id):
    logger.info(f"🚀 Triggered Secret Mirror System for Source Chat ID: {source_chat_id}")
    
    if not await start_secret_clients():
        logger.error("❌ Mirroring Aborted: Secret clients could not be started.")
        return

    try:
        mapping = await mirror_col.find_one({"source_id": str(source_chat_id)})
        
        if not mapping:
            logger.info("🆕 No existing backup channel found. Creating a new one...")
            safe_title = f"{source_chat_title[:100]} [Backup]" if source_chat_title else f"Unknown_Backup_{source_chat_id}"
            
            # 1. Create Channel
            logger.info(f"⏳ Creating channel '{safe_title}'...")
            new_chat = await SECRET_USER.create_channel(title=safe_title)
            logger.info(f"✅ New Channel Created! ID: {new_chat.id}")
            
            # 2. Get Bot ID directly
            secret_bot_info = await SECRET_BOT.get_me()
            bot_id = secret_bot_info.id
            
            await asyncio.sleep(2) # Anti-Spam
            logger.info("🔄 Promoting Secret Bot directly to Admin (Fix applied)...")
            
            # 3. DIRECTLY Promote to Admin (No add_chat_members used)
            await SECRET_USER.promote_chat_member(
                chat_id=new_chat.id, 
                user_id=bot_id, 
                privileges=ChatPrivileges(
                    can_manage_chat=True,
                    can_post_messages=True, 
                    can_edit_messages=True, 
                    can_delete_messages=True,
                    can_invite_users=True
                )
            )
            logger.info("✅ Secret Bot is now Admin in the new channel!")
            
            mapping = {"source_id": str(source_chat_id), "secret_chat_id": new_chat.id}
            await mirror_col.insert_one(mapping)
        else:
            logger.info(f"📂 Found existing backup channel ID: {mapping['secret_chat_id']}")
        
        secret_chat_id = mapping["secret_chat_id"]

        await asyncio.sleep(1) 
        logger.info("🔄 Forwarding (Copying) file from LOG_GROUP to Secret Channel...")
        await SECRET_BOT.copy_message(
            chat_id=secret_chat_id,
            from_chat_id=log_group_id,
            message_id=log_msg_id
        )
        logger.info("🎉 SUCCESS: File Successfully Mirrored to Secret Backup Channel!")
        
    except Exception as e:
        logger.error(f"⚠️ Secret Mirror CRITICAL Error: {e}", exc_info=True)

# ==========================================
# 🟢 4. BOT TOKEN SETUP COMMAND
# ==========================================

@MAIN_BOT.on_message(filters.command("setsecretbot") & filters.user(OWNER_ID))
async def set_secret_bot(c, m):
    if len(m.command) < 2:
        return await m.reply("❌ Send bot token too: `/setsecretbot 1234:ABC...`")
    await init_secret_db()
    if config_col is not None:
        await config_col.update_one({"_id": "secret_credentials"}, {"$set": {"bot_token": m.command[1]}}, upsert=True)
        await m.reply("✅ Secret Bot Token Saved in Secret Database!")

asyncio.get_event_loop().create_task(init_secret_db())