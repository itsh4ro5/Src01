import os
import sys
import random
import asyncio
from pyrogram import idle
from pyrogram.types import BotCommand  

# 🟢 UVLOOP WAPAS ADD KIYA GAYA HAI SPEED KE LIYE
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    print("⚡ uvloop activated! Async operations will run at max speed.")
except ImportError:
    print("⚠️ uvloop not installed. Standard asyncio will be used.")

from shared_client import start_client, app
import utils.func as global_state

async def human_behavior_routine():
    while True:
        active_time = random.uniform(10500.5, 11000.2)
        await asyncio.sleep(active_time)
        global_state.IS_PAUSED = True
        sleep_time = random.uniform(1150.7, 1250.3)
        await asyncio.sleep(sleep_time)
        global_state.IS_PAUSED = False

async def setup_bot_commands():
    try:
        await app.set_bot_commands([
            BotCommand("start", "Start the bot & check status"),
            BotCommand("login", "Login to save private restricted content"),
            BotCommand("logout", "Logout from your current session"),
            BotCommand("batch", "Extract multiple restricted messages"),
            BotCommand("single", "Extract a single restricted message"),
            BotCommand("forward", "Toggle Fast Forward Mode"),
            BotCommand("setbot", "Set your custom bot token"),
            BotCommand("rembot", "Remove your custom bot token")
        ])
        print("✅ Bot command menu set successfully!")
    except Exception as e:
        print(f"⚠️ Failed to set bot commands: {e}")

async def main():
    print("🚀 Initializing Bot Engine with Speed Boost...")
    try:
        await start_client()
    except Exception as e:
        print(f"❌ Error starting clients: {e}")
        return
        
    await setup_bot_commands()  
    asyncio.create_task(human_behavior_routine())
    
    print("✅ Bot is online and listening to your commands at Max Speed!")
    # 🟢 Yahan se bot commands sune ga
    await idle()

if __name__ == "__main__":
    try:
        # Loop configuration for uvloop
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("🛑 Shutting down gracefully...")
    except Exception as e:
        print(f"⚠️ CRITICAL ERROR: {e}")