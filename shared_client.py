from telethon import TelegramClient
from telethon.sessions import MemorySession
from config import API_ID, API_HASH, BOT_TOKEN, STRING
from pyrogram import Client
import sys

client = TelegramClient(MemorySession(), API_ID, API_HASH)

# 🟢 SMOOTH & STABLE MODE: Fluctuation rokne ke liye '3' set kiya hai
app = Client(
    "pyrogrambot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    max_concurrent_transmissions=2  # Ab speed achanak se jump nahi karegi
)

userbot = Client(
    "4gbbot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    session_string=STRING,
    max_concurrent_transmissions=5  # Yahan bhi '3' kar diya hai
) if STRING else None

async def start_client():
    if not client.is_connected():
        await client.start(bot_token=BOT_TOKEN)
        print("SpyLib (Telethon) started in Memory Mode...")
    
    if STRING and userbot:
        try:
            await userbot.start()
            print("Userbot started cleanly...")
        except Exception as e:
            print(f"Hey honey!! check your premium string session, it may be invalid or expired: {e}")
            sys.exit(1)
            
    await app.start()
    print("Pyro App Started cleanly...")
    return client, app, userbot