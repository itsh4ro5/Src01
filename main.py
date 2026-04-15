import os
import sys
import random
import time
import asyncio
from pyrogram import idle # 🟢 NAYA IMPORT: Bot ko zinda rakhne ke liye
from pyrogram.types import BotCommand  

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print("⚡ uvloop activated! Async operations will run at max speed.")
except ImportError:
    print("⚠️ uvloop not installed. Standard asyncio will be used.")

from shared_client import start_client, app
import utils.func as global_state

async def human_behavior_routine():
    while True:
        active_time = random.uniform(10500.5, 11000.2)
        await asyncio.sleep(active_time)
        print("Taking a ~20-minute human-like break to prevent bans...")
        global_state.IS_PAUSED = True
        sleep_time = random.uniform(1150.7, 1250.3)
        await asyncio.sleep(sleep_time)
        print("Waking up from break...")
        global_state.IS_PAUSED = False

async def setup_bot_commands():
    try:
        await app.set_bot_commands([
            BotCommand("start", "Start the bot & check status"),
            BotCommand("login", "Login to save private restricted content"),
            BotCommand("logout", "Logout from your current session"),
            BotCommand("batch", "Extract multiple restricted messages"),
            BotCommand("single", "Extract a single restricted message"),
            BotCommand("dl", "Download video from YouTube/Insta/etc"),
            BotCommand("adl", "Download audio from YouTube/Insta/etc"),
            BotCommand("forward", "Toggle Fast Forward Mode (No Download)"),
            BotCommand("settings", "🎨 Settings & Customize Thumbnail"),
            BotCommand("id", "🆔 Get Chat/User ID"),
            BotCommand("cancel", "Cancel the currently active batch task"),
            BotCommand("setbot", "Set your custom bot token"),
            BotCommand("rembot", "Remove your custom bot token")
        ])
        print("✅ Bot command menu set successfully!")
    except Exception as e:
        print(f"⚠️ Failed to set bot commands: {e}")

async def main():
    try:
        # Pyrogram automatically plugins load kar lega shared_client.py ki wajah se
        await start_client()
    except Exception as e:
        print(f"Error during client start: {e}")
        
    await setup_bot_commands()  
    asyncio.create_task(human_behavior_routine())
    
    print("✅ Bot is fully active and listening to commands!")
    # 🟢 FIX: Blocking while loop hatakar pyrogram ka idle lagaya
    await idle()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    print("Starting clients ...")
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"⚠️ CRITICAL ERROR: {e}")
        print("⏳ Bot is facing a FloodWait or Server Ban. Sleeping for 15 Minutes to clear limits...")
        time.sleep(900)  
        print("🔄 Restarting now...")
        sys.exit(1)
    finally:
        try:
            loop.close()
        except Exception:
            pass