import os
import sys
import random
import time
import asyncio
import importlib
import logging
import traceback
from datetime import datetime
from utils.func import premium_users_collection
from pyrogram.types import BotCommand  
from pyrogram import idle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler()] 
)
logger = logging.getLogger(__name__)

# 🟢 SPEED BOOST: Activate Ultra-Fast Async Engine
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print("⚡ uvloop activated! Async operations will run at max speed.")
except ImportError:
    print("⚠️ uvloop not installed. Standard asyncio will be used. (pip install uvloop)")

from shared_client import start_client, app
import utils.func as global_state

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

# --- 🟢 SMART VPS CLEANUP ROUTINE ---
async def auto_cleanup_routine():
    """Har 12 ghante me kachra saaf karega taaki VPS full na ho"""
    while True:
        try:
            logger.info("🧹 Starting VPS Auto-Cleanup routine...")
            current_time = time.time()
            deleted_files = 0
            freed_space = 0
            
            # Temporary files ki extensions
            exts = ('.mp4', '.mkv', '.avi', '.pdf', '.zip', '.jpg', '.png', '.mp3', '.webm')
            
            # Current directory me saari files check karega
            for filename in os.listdir('.'):
                if filename.lower().endswith(exts):
                    file_path = os.path.join('.', filename)
                    # Agar file 24 ghante (86400 seconds) se purani hai
                    if os.path.isfile(file_path) and (current_time - os.path.getmtime(file_path)) > 86400:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_files += 1
                        freed_space += file_size
            
            if deleted_files > 0:
                freed_mb = freed_space / (1024 * 1024)
                logger.info(f"✅ Cleanup Done: Deleted {deleted_files} old files. Freed {freed_mb:.2f} MB space.")
            else:
                logger.info("✅ Cleanup Done: No old files found. Server is clean!")
                
        except Exception as e:
            logger.error(f"❌ Cleanup Error: {e}")
            
        # Agli baar 12 ghante (43200 seconds) baad chalega
        await asyncio.sleep(43200)
# ------------------------------------

# --- 🟢 PREMIUM AUTO-DEMOTION & ALERT ROUTINE ---
async def premium_expiry_routine():
    """Har 1 ghante me check karega ki kiska plan expire hua hai aur alert bhejega"""
    while True:
        try:
            now = datetime.now()
            # Un users ko dhoondo jinka expiry time aaj se pehle ka ho chuka hai
            expired_users = premium_users_collection.find({"subscription_end": {"$lt": now}})
            
            async for user in expired_users:
                user_id = user.get("user_id")
                if user_id:
                    try:
                        # User ko alert bhejna
                        await app.send_message(
                            user_id, 
                            "⚠️ **Notice:** Your Premium Subscription has expired! You have been downgraded to the Free plan. Contact the owner to renew."
                        )
                    except Exception as e:
                        # Agar user ne bot block kar diya ho
                        logger.warning(f"Failed to send expiry alert to {user_id}: {e}")
                    
                    # Database se officially delete karna
                    await premium_users_collection.delete_one({"user_id": user_id})
                    logger.info(f"⬇️ Demoted user {user_id} to Free plan due to expiry.")
                    
        except Exception as e:
            logger.error(f"❌ Premium Expiry Routine Error: {e}")
            
        # Agli checking 1 ghante (3600 seconds) baad hogi
        await asyncio.sleep(3600)
# ------------------------------------------------

async def load_and_run_plugins():
    plugin_dir = "plugins"
    plugins = [f[:-3] for f in os.listdir(plugin_dir) if f.endswith(".py") and f != "__init__.py"]

    for plugin in plugins:
        try:
            importlib.import_module(f"plugins.{plugin}")
            print(f"✅ Loaded plugin: {plugin}")
        except Exception as e:
            logger.error(f"❌ ERROR loading plugin '{plugin}':", exc_info=True)

async def main():
    await start_client()  # Pehle client start karo
    await load_and_run_plugins() # Fir plugins load karo
    await setup_bot_commands()  
    
    # 🟢 Start the Background Tasks
    asyncio.create_task(auto_cleanup_routine())
    asyncio.create_task(premium_expiry_routine()) # <-- YE NAYI LINE ADD KI HAI
    
    logger.info("🚀 Bot is Online and Ready to take commands!")
    await idle()  # Ye bot ko active rakhega saari commands receive karne ke liye

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    print("Starting clients ...")
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"⚠️ CRITICAL ERROR: {e}")
        time.sleep(10)  
        print("🔄 Restarting now...")
        os.execv(sys.executable, ['python'] + sys.argv)
    finally:
        try:
            loop.close()
        except Exception:
            pass