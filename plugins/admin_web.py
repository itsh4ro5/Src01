import string
import random
from telethon import events
from shared_client import client as bot_client
from config import OWNER_ID
from utils.func import admin_auth_collection, is_private_chat, get_display_name

def generate_web_password(length=10):
    """Secure random password generate karne ke liye"""
    chars = string.ascii_letters + string.digits + "@#$"
    return ''.join(random.choice(chars) for _ in range(length))

@bot_client.on(events.NewMessage(pattern='/webpass'))
async def generate_pass_handler(event):
    # Sirf private chat me work karega taaki password group me leak na ho
    if not await is_private_chat(event):
        return
    
    user_id = event.sender_id
    
    # Check karega ki user OWNER_ID list me hai ya nahi
    if user_id not in OWNER_ID:
        await event.respond("❌ **Access Denied:** You are not authorized to generate web passwords.")
        return

    # Admin ka naam aur naya password generate karna
    sender = await event.get_sender()
    admin_name = get_display_name(sender)
    new_password = generate_web_password()
    
    # MongoDB me password aur details save karna (Upsert = agar pehle se hai toh update karega)
    await admin_auth_collection.update_one(
        {"admin_id": user_id},
        {"$set": {"password": new_password, "admin_name": admin_name}},
        upsert=True
    )
    
    # Admin ko secure message bhejna
    await event.respond(
        f"🔐 **Web Admin Login Details Generated** 🔐\n\n"
        f"👤 **Your Telegram ID:** `{user_id}`\n"
        f"🔑 **Your Password:** `{new_password}`\n\n"
        f"🌐 **Dashboard URL:** `https://your-huggingface-space-url.hf.space/admin`\n\n"
        f"⚠️ *Ise copy karein aur dashboard par login karein. Ye password jab chahein /webpass bhej kar reset kar sakte hain.*"
    )