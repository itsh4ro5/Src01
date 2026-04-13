import string
import random
from telethon import events
from shared_client import client as bot_client
from config import OWNER_ID

# 👇 is_premium_user ko bhi import kar liya gaya hai
from utils.func import admin_auth_collection, is_private_chat, get_display_name, is_premium_user

def generate_web_password(length=10):
    """Secure random password generate karne ke liye"""
    chars = string.ascii_letters + string.digits + "@#$"
    return ''.join(random.choice(chars) for _ in range(length))

@bot_client.on(events.NewMessage(pattern='/webpass'))
async def generate_pass_handler(event):
    # Sirf private chat me work karega
    if not await is_private_chat(event):
        return
    
    user_id = event.sender_id
    
    # 👇 NEW LOGIC: Check if user is Boss(Owner) OR Admin(Premium)
    is_boss = user_id in OWNER_ID
    is_admin = await is_premium_user(user_id)
    
    if not (is_boss or is_admin):
        await event.respond("❌ **Access Denied:** You must be an Admin (Premium User) or the Boss to generate a web password.")
        return

    # User ka naam aur naya password generate karna
    sender = await event.get_sender()
    admin_name = get_display_name(sender)
    new_password = generate_web_password()
    
    # MongoDB me password aur details save karna
    await admin_auth_collection.update_one(
        {"admin_id": user_id},
        {"$set": {"password": new_password, "admin_name": admin_name}},
        upsert=True
    )
    
    # Role ke hisab se tag dena
    role_tag = "Boss 👑" if is_boss else "Admin 💼"
    
    # Secure message bhejna
    await event.respond(
        f"🔐 **{role_tag} - Login Details Generated** 🔐\n\n"
        f"👤 **Your Telegram ID:** `{user_id}`\n"
        f"🔑 **Your Password:** `{new_password}`\n\n"
        f"🌐 **Dashboard URL:** `https://your-huggingface-space-url.hf.space/admin`\n\n"
        f"⚠️ *Ye password jab chahein /webpass bhej kar reset kar sakte hain.*"
    )