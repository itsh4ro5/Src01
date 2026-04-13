import string
import random
from shared_client import client as bot_client
from telethon import events
from config import OWNER_ID
from utils.func import admin_auth_collection, is_private_chat, get_display_name

def generate_web_password(length=10):
    chars = string.ascii_letters + string.digits + "@#$"
    return ''.join(random.choice(chars) for _ in range(length))

@bot_client.on(events.NewMessage(pattern='/webpass'))
async def generate_pass_handler(event):
    if not await is_private_chat(event):
        return
    
    user_id = event.sender_id
    if user_id not in OWNER_ID: # Sirf authorized admins ke liye
        await event.respond("❌ You are not authorized to generate web passwords.")
        return

    admin_name = get_display_name(await event.get_sender())
    new_password = generate_web_password()
    
    # Save to MongoDB (upsert so old password gets overwritten)
    await admin_auth_collection.update_one(
        {"admin_id": user_id},
        {"$set": {"password": new_password, "admin_name": admin_name}},
        upsert=True
    )
    
    await event.respond(
        f"🔐 **Web Admin Login Details** 🔐\n\n"
        f"👤 **Telegram ID:** `{user_id}`\n"
        f"🔑 **Password:** `{new_password}`\n\n"
        f"⚠️ *Ye password copy karein aur dashboard par login karein.*"
    )