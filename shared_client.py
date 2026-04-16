from telethon import TelegramClient
from telethon.sessions import MemorySession
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN, STRING
import sys

# 🟢 FIX: Pyrogram native plugin loader activated! 
app = Client(
    "pyrogrambot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")
)

client = TelegramClient(MemorySession(), API_ID, API_HASH)
userbot = Client("4gbbot", api_id=API_ID, api_hash=API_HASH, session_string=STRING) if STRING else None

async def start_client():
    if not client.is_connected():
        await client.start(bot_token=BOT_TOKEN)
        print("✅ Telethon started in Memory Mode...")
    
    if userbot:
        try:
            await userbot.start()
            print("✅ Premium Userbot started...")
        except Exception as e:
            print(f"⚠️ Userbot session error: {e}")
            
    await app.start()
    print("✅ Pyrogram App Started...")
    return client, app, userbot