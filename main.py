import os
import sys
import random
import time
import asyncio
import importlib
from pyrogram.types import BotCommand  
from pyrogram import idle# 🟢 Bot ko background me jagaye rakhne ke liye
from pyrogram.errors import FloodWait

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

async def load_and_run_plugins():
    try:
        await start_client()
    except Exception as e:
        print(f"Error during client start: {e}")
        
    plugin_dir = "plugins"
    plugins = [f[:-3] for f in os.listdir(plugin_dir) if f.endswith(".py") and f != "__init__.py"]

    for plugin in plugins:
        try:
            # 🟢 FIX: Ab koi plugin crash hua toh wo aage badh jayega bina bot ko roke
            module = importlib.import_module(f"plugins.{plugin}")
            if hasattr(module, f"run_{plugin}_plugin"):
                print(f"Running {plugin} plugin...")
                await getattr(module, f"run_{plugin}_plugin")()  
        except Exception as e:
            print(f"⚠️ Failed to load plugin '{plugin}': {e}") # Isse error terminal me dikhega # Chup chap aage badh jayega, crash nahi hoga

async def main():
    await load_and_run_plugins()
    await setup_bot_commands()  
    asyncio.create_task(human_behavior_routine())
    
    print("🚀 Bot is Online and Ready to take commands!")
    
    # 🟢 FIX: Block wala while loop hta kar idle lagaya, isse bot har command ka turant response dega.
    await idle()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    print("Starting clients ...")
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Shutting down...")
    except FloodWait as e:
        wait_time = e.value + 20
        print(f"⏳ Global FloodWait detect hua! Telegram ne {e.value}s bola hai. Hum rukenge...")
        time.sleep(wait_time) 
        print("🔄 Buffer complete. Auto-Restarting Bot now...")
        # Graceful restart bina bot ko mare:
        os.execv(sys.executable, ['python'] + sys.argv)
    finally:
        try:
            loop.close()
        except Exception:
            pass