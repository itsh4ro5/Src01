# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  

import asyncio
from shared_client import start_client, app
import importlib
import os
import sys
import random
import utils.func as global_state
from pyrogram.types import BotCommand  # Command menu ke liye import kiya hai

async def human_behavior_routine():
    while True:
        # Lagbhag 3 ghante (10500 se 11000 seconds) tak active rahega
        active_time = random.uniform(10500.5, 11000.2)
        await asyncio.sleep(active_time)
        
        print("Taking a ~20-minute human-like break to prevent bans...")
        global_state.IS_PAUSED = True
        
        # Lagbhag 20 mins (1150 se 1250 seconds) ka decimal random break
        sleep_time = random.uniform(1150.7, 1250.3)
        await asyncio.sleep(sleep_time)
        
        print("Waking up from break...")
        global_state.IS_PAUSED = False

async def load_and_run_plugins():
    await start_client()
    plugin_dir = "plugins"
    plugins = [f[:-3] for f in os.listdir(plugin_dir) if f.endswith(".py") and f != "__init__.py"]

    for plugin in plugins:
        module = importlib.import_module(f"plugins.{plugin}")
        if hasattr(module, f"run_{plugin}_plugin"):
            print(f"Running {plugin} plugin...")
            await getattr(module, f"run_{plugin}_plugin")()  

# 🟢 BOT MENU COMMANDS SETUP FUNCTION
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
            BotCommand("cancel", "Cancel the currently active batch task"),
            BotCommand("setbot", "Set your custom bot token (e.g., /setbot <token>)"),
            BotCommand("rembot", "Remove your custom bot token")
        ])
        print("✅ Bot command menu set successfully!")
    except Exception as e:
        print(f"⚠️ Failed to set bot commands: {e}")

async def main():
    await load_and_run_plugins()
    await setup_bot_commands()  # Yahan command menu setup ko call kiya gaya hai
    asyncio.create_task(human_behavior_routine())
    while True:
        await asyncio.sleep(1)  

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    print("Starting clients ...")
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(e)
        sys.exit(1)
    finally:
        try:
            loop.close()
        except Exception:
            pass