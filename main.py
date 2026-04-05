# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  

import os
import sys
import random
import time
import asyncio
import importlib
from pyrogram import filters
from pyrogram.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

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

# ==========================================
# 🎨 FONTS & COLORS CONFIGURATION
# ==========================================
# 📂 FONT FOLDER PATH - Is folder me aapko apni saari .ttf files upload karni hain
FONT_DIR = "fonts"
if not os.path.exists(FONT_DIR):
    os.makedirs(FONT_DIR)

AVAILABLE_FONTS = {
    "default.ttf": "Standard Font",
    "impact.ttf": "𝗕𝗢𝗟𝗗 𝗜𝗠𝗣𝗔𝗖𝗧",
    "hacker.ttf": "🄷🄰🄲🄺🄴🅁 🄶🄻🄸🅃🄲🄷",
    "comic.ttf": "𝘊𝘰𝘮𝘪𝘤 𝘚𝘵𝘺𝘭𝘦",
    "neon.ttf": "Nҽ𝘰n Lιg𝘩t",
    "cyber.ttf": "C Y B E R",
    "pixel.ttf": "P1X3L 8-B1T",
    "roboto.ttf": "Roboto Clean",
    "arial_bold.ttf": "Arial Bold",
    "gothic.ttf": "𝕲𝘰𝘵𝘩𝘪𝘤 𝕯𝘢𝘳𝘬",
    "matrix.ttf": "MΛTRIX",
    "vintage.ttf": "𝓥𝘪𝘯𝘵𝘢𝘨𝘦 𝓡𝘦𝘵𝘳𝘰",
    "future.ttf": "F U T U R E",
    "monster.ttf": "M O N S T E R",
    "cursive.ttf": "𝓒𝓾𝓻𝓼𝓲𝓿𝓮 𝓛𝓸𝓿𝓮",
    "elegant.ttf": "𝔼𝘭𝘦𝘨𝘢𝘯𝘵 𝕾𝘦𝘳𝘪𝘧",
    "space.ttf": "S P A C E",
    "bold_italic.ttf": "𝘽𝗼𝙡𝗱 𝙄𝙩𝙖𝙡𝙞𝙘",
    "typewriter.ttf": "Tʏp𝘦wʀiᴛeʀ",
    "graffiti.ttf": "G𝕣a𝘧fιt𝘪",
    "ninja.ttf": "🥷 N I N J A"
}

AVAILABLE_COLORS = {
    "white": "⚪ White", "black": "⚫ Black", "red": "🔴 Red", "blue": "🔵 Blue", 
    "green": "🟢 Green", "yellow": "🟡 Yellow", "orange": "🟠 Orange", "purple": "🟣 Purple",
    "brown": "🟤 Brown", "pink": "🌸 Pink", "gray": "🔘 Gray", "silver": "🪙 Silver",
    "#39FF14": "🟢 Neon Green", "#00FFFF": "🔵 Cyan / Aqua", "#FF00FF": "🟣 Magenta", 
    "#FF1493": "💖 Deep Pink", "#00FF00": "🟩 Lime", "#FFFF00": "🟨 Cyber Yellow",
    "#FF4500": "🔥 Orange Red", "#8A2BE2": "🎀 Deep Pink", "#7FFF00": "🎾 Chartreuse",
    "#FFD700": "🟡 Gold", "#DAA520": "🍯 Goldenrod", "#B8860B": "🪙 Dark Goldenrod",
    "#CD7F32": "🏆 Peru / Bronze", "#C0C0C0": "⚙️ Silver Pro", "#E5E4E2": "💿 Platinum",
    "#1E90FF": "🌊 Dodger Blue", "#00BFFF": "💦 Deep Sky Blue", "#4682B4": "👖 Steel Blue",
    "#4169E1": "🧿 Royal Blue", "#000080": "🌌 Navy", "#191970": "🌃 Midnight Blue",
    "#00CED1": "💧 Dark Turquoise", "#5F9EA0": "🎽 Cadet Blue", "#ADD8E6": "🧊 Light Blue",
    "#DC143C": "🩸 Crimson", "#B22222": "🧱 Firebrick", "#8B0000": "🍷 Dark Red",
    "#FF69B4": "👙 Hot Pink", "#FFB6C1": "🩰 Light Pink", "#C71585": "🌺 Medium Violet Red",
    "#FA8072": "🍣 Salmon", "#E9967A": "🦐 Dark Salmon", "#F08080": "🥩 Light Coral",
    "#228B22": "🌲 Forest Green", "#006400": "🌳 Dark Green", "#2E8B57": "🌿 Sea Green",
    "#3CB371": "🍀 Medium Sea Green", "#8FBC8F": "🔋 Dark Sea Green", "#98FB98": "🍵 Pale Green",
    "#00FA9A": "🍈 Medium Spring Green", "#9ACD32": "🥝 Yellow Green", "#6B8E23": "🫒 Olive Drab",
    "#800080": "🍇 Purple", "#9370DB": "🍆 Medium Purple", "#8B008B": "🔮 Dark Magenta",
    "#9400D3": "🍠 Dark Violet", "#9932CC": "🌂 Dark Orchid", "#BA55D3": "👚 Medium Orchid",
    "#DDA0DD": "🪻 Plum", "#EE82EE": "🪁 Violet", "#DA70D6": "🪀 Orchid",
    "#FF8C00": "🎃 Dark Orange", "#D2691E": "🐫 Goldenrod", "#8B4513": "👞 Saddle Brown",
    "#A0522D": "🧳 Sienna", "#D2B48C": "🐪 Tan", "#DEB887": "🪵 Burlywood",
    "#F4A460": "🪑 Sandy Brown", "#BC8F8F": "🏕️ Rosy Brown", "#F0E68C": "🌾 Khaki",
    "#FFDAB9": "🍑 Peach Puff", "#FFE4B5": "🥟 Moccasin", "#FFEFD5": "🧈 Papaya Whip",
    "#FFFACD": "🍋 Lemon Chiffon", "#FAFAD2": "🍌 Light Goldenrod", "#E0FFFF": "🧼 Light Cyan",
    "#F0FFF0": "🍯 Honeydew", "#F5FFFA": "🥛 Mint Cream", "#F0F8FF": "🥣 Alice Blue",
    "#FFF0F5": "🧂 Lavender Blush", "#FFE4E1": "🌸 Misty Rose", "#FFF5EE": "🐚 Seashell",
    "#2F4F4F": "🪨 Dark Slate Gray", "#708090": "🗻 Slate Gray", "#A9A9A9": "🐭 Dark Gray",
    "#696969": "🐘 Dim Gray", "#778899": "🦈 Light Slate Gray", "#2C3E50": "🌚 Dark Blue Gray"
}

# ==========================================
# 🛠️ UI COMMANDS: ID & SETTINGS
# ==========================================
@app.on_message(filters.command("id"))
async def get_id_cmd(client, message):
    text = f"🆔 **Current Chat ID:** `{message.chat.id}`\n"
    if message.reply_to_message:
        if message.reply_to_message.forward_from_chat: 
            text += f"📢 **Forwarded Chat ID:** `{message.reply_to_message.forward_from_chat.id}`\n"
        elif message.reply_to_message.forward_from: 
            text += f"👤 **Forwarded User ID:** `{message.reply_to_message.forward_from.id}`\n"
    await message.reply(text)

@app.on_message(filters.command("settings") & filters.private)
async def settings_command(client, message):
    user_id = message.from_user.id
    current_font = await global_state.get_user_data_key(user_id, "thumb_font", "default.ttf")
    current_color = await global_state.get_user_data_key(user_id, "thumb_color", "white")
    
    font_name = AVAILABLE_FONTS.get(current_font, "Standard Font")
    color_name = AVAILABLE_COLORS.get(current_color, "⚪ White")
    
    text = (
        "⚙️ **BOT SETTINGS PANEL**\n\n"
        f"🎨 **Current Thumbnail Style:**\n"
        f"• Font: {font_name}\n"
        f"• Color: {color_name}\n\n"
        "Niche diye gaye buttons se apni settings customize karein:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎨 Thumbnail Customize", callback_data="menu_thumb_custom")],
        [InlineKeyboardButton("❌ Close", callback_data="close_menu")]
    ])
    await message.reply(text, reply_markup=keyboard)

@app.on_callback_query(filters.regex(r"^menu_|^set_|^close_"))
async def callback_handler(client, call: CallbackQuery):
    user_id = call.from_user.id
    data = call.data
    
    if data == "close_menu":
        await call.message.delete()
        
    elif data == "menu_thumb_custom":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔠 Change Font Style", callback_data="menu_fonts_0")],
            [InlineKeyboardButton("🖌 Change Font Color", callback_data="menu_colors_0")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_main")]
        ])
        await call.message.edit_text("🎨 **Thumbnail Customization**\nKya change karna chahte hain?", reply_markup=keyboard)
        
    elif data == "menu_main":
        current_font = await global_state.get_user_data_key(user_id, "thumb_font", "default.ttf")
        current_color = await global_state.get_user_data_key(user_id, "thumb_color", "white")
        font_name = AVAILABLE_FONTS.get(current_font, "Standard Font")
        color_name = AVAILABLE_COLORS.get(current_color, "⚪ White")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎨 Thumbnail Customize", callback_data="menu_thumb_custom")],
            [InlineKeyboardButton("❌ Close", callback_data="close_menu")]
        ])
        await call.message.edit_text(
            f"⚙️ **BOT SETTINGS PANEL**\n\n🎨 **Current Style:**\n• Font: {font_name}\n• Color: {color_name}", 
            reply_markup=keyboard
        )
        
    # 🟢 PAGINATED FONTS MENU
    elif data.startswith("menu_fonts_"):
        page = int(data.split("_")[2])
        font_keys = list(AVAILABLE_FONTS.keys())
        per_page = 10
        start = page * per_page
        end = start + per_page
        current_fonts = font_keys[start:end]
        
        buttons = []
        for f_file in current_fonts:
            buttons.append([InlineKeyboardButton(AVAILABLE_FONTS[f_file], callback_data=f"set_font_{f_file}")])
            
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"menu_fonts_{page-1}"))
        if end < len(font_keys):
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"menu_fonts_{page+1}"))
        
        if nav_row: buttons.append(nav_row)
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_thumb_custom")])
        
        await call.message.edit_text(
            f"🔠 **Select Font Style (Page {page+1}):**\n*(Ensure {FONT_DIR}/ folder has these .ttf files)*", 
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    # 🟢 PAGINATED COLORS MENU
    elif data.startswith("menu_colors_"):
        page = int(data.split("_")[2])
        color_keys = list(AVAILABLE_COLORS.keys())
        per_page = 20 # 2 columns x 10 rows
        start = page * per_page
        end = start + per_page
        current_colors = color_keys[start:end]
        
        buttons = []
        row = []
        for c_code in current_colors:
            row.append(InlineKeyboardButton(AVAILABLE_COLORS[c_code], callback_data=f"set_color_{c_code}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row: buttons.append(row)
        
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"menu_colors_{page-1}"))
        if end < len(color_keys):
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"menu_colors_{page+1}"))
            
        if nav_row: buttons.append(nav_row)
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_thumb_custom")])
        
        await call.message.edit_text(
            f"🖌 **Select Font Color (Page {page+1}):**", 
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    elif data.startswith("set_font_"):
        new_font = data.split("set_font_")[1]
        await global_state.save_user_data(user_id, "thumb_font", new_font)
        await call.answer(f"Font changed to {AVAILABLE_FONTS.get(new_font)}!", show_alert=True)
        await callback_handler(client, call._modify(data="menu_thumb_custom"))
        
    elif data.startswith("set_color_"):
        new_color = data.split("set_color_")[1]
        await global_state.save_user_data(user_id, "thumb_color", new_color)
        await call.answer(f"Color changed to {AVAILABLE_COLORS.get(new_color)}!", show_alert=True)
        await callback_handler(client, call._modify(data="menu_thumb_custom"))

# ==========================================
# 🧠 CORE SYSTEM & PLUGINS LOADER
# ==========================================
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
            BotCommand("settings", "🎨 Customize Thumbnail Fonts & Colors"),
            BotCommand("id", "🆔 Get Chat or User ID"),
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
        module = importlib.import_module(f"plugins.{plugin}")
        if hasattr(module, f"run_{plugin}_plugin"):
            print(f"Running {plugin} plugin...")
            await getattr(module, f"run_{plugin}_plugin")()  

async def main():
    await load_and_run_plugins()
    await setup_bot_commands()  
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
