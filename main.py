# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  

import asyncio
from shared_client import start_client
import importlib
import os
import sys
import random
import utils.func as global_state

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

async def main():
    await load_and_run_plugins()
    # Start the human behavior sleep cycle in background
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