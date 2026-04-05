import os
import re
import time
import math
import asyncio
import logging
import subprocess
import urllib3
import aiohttp
from datetime import datetime, timedelta

# 🟢 IMPORT NEW CONFIGURATION FILE
from theme_config import AVAILABLE_FONTS, AVAILABLE_COLORS, FONT_DIR

# 🟢 SPEED BOOST: Activate Ultra-Fast Async Engine
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print("⚡ uvloop activated! Async operations will run at max speed.")
except ImportError:
    print("⚠️ uvloop not installed. Standard asyncio will be used.")

# 🟢 PDF Watermark Library
try:
    import fitz
except ImportError:
    fitz = None

# 🟢 Fast Downloader Library
try:
    import yt_dlp
except ImportError:
    yt_dlp = None

# 🟢 Pillow Library for Advanced Thumbnail Font Watermarking
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image, ImageDraw, ImageFont = None, None, None
    print("⚠️ Pillow not installed! Run 'pip install Pillow'")

from pyrogram import Client, filters, enums
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, FloodWait, PeerIdInvalid
from pyrogram.types import Message, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from motor.motor_asyncio import AsyncIOMotorClient
from flask import Flask
from threading import Thread

# Logs Optimization
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger("pyrogram").setLevel(logging.WARNING) 
logging.getLogger("asyncio").setLevel(logging.WARNING) 
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. CONFIGURATION
# ==========================================
API_ID = int(os.environ.get("API_ID", "123456")) 
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI", "YOUR_MONGODB_URI")
OWNER_ID = int(os.environ.get("OWNER_ID", "123456789")) 

DEVICE_MODEL = "realme P3 Pro 5G"
SYSTEM_VERSION = "Android 14"
APP_VERSION = "12.5.2"

app = Client("m3u8_pro_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, sleep_threshold=120)
db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client["telegram_bot"]
users_col = db["users"]
queue_col = db["queue"]
bot_chats_col = db["bot_chats"] 

web_app = Flask(__name__)
@web_app.route('/')
def home(): return "Pro Max Bot is Alive!"
def run_web(): 
    try: web_app.run(host="0.0.0.0", port=7860)
    except: pass

login_clients = {} 

# ==========================================
# UI SETTINGS & CALLBACKS (PAGINATED)
# ==========================================
@app.on_message(filters.command("settings") & filters.private)
async def settings_command(client, message):
    user_id = message.from_user.id
    user = await users_col.find_one({"_id": user_id}) or {}
    
    current_font = user.get("thumb_font", "default.ttf")
    current_color = user.get("thumb_color", "white")
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
        user = await users_col.find_one({"_id": user_id}) or {}
        current_font = user.get("thumb_font", "default.ttf")
        current_color = user.get("thumb_color", "white")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎨 Thumbnail Customize", callback_data="menu_thumb_custom")],
            [InlineKeyboardButton("❌ Close", callback_data="close_menu")]
        ])
        await call.message.edit_text(
            f"⚙️ **BOT SETTINGS PANEL**\n\n🎨 **Current Style:**\n• Font: {AVAILABLE_FONTS.get(current_font, 'Standard Font')}\n• Color: {AVAILABLE_COLORS.get(current_color, '⚪ White')}", 
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
            f"🔠 **Select Font Style (Page {page+1}):**\n*(Upload {FONT_DIR}/ folder me apni TTF files dalna na bhulein)*", 
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    # 🟢 PAGINATED COLORS MENU (100+ Colors handle karne ke liye)
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
        await users_col.update_one({"_id": user_id}, {"$set": {"thumb_font": new_font}}, upsert=True)
        await call.answer(f"Font changed to {AVAILABLE_FONTS.get(new_font)}!", show_alert=True)
        await callback_handler(client, call._modify(data="menu_thumb_custom"))
        
    elif data.startswith("set_color_"):
        new_color = data.split("set_color_")[1]
        await users_col.update_one({"_id": user_id}, {"$set": {"thumb_color": new_color}}, upsert=True)
        await call.answer(f"Color changed to {AVAILABLE_COLORS.get(new_color)}!", show_alert=True)
        await callback_handler(client, call._modify(data="menu_thumb_custom"))

# ==========================================
# HELPERS & PROCESSING
# ==========================================
async def check_access(user_id):
    if user_id == OWNER_ID: return True
    user = await users_col.find_one({"_id": user_id})
    if user and user.get("role") == "admin": return True
    return False

def format_bytes(size):
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power; n += 1
    return f"{size:.2f} {power_labels[n]}B"

async def safe_edit(message, text):
    try: await message.edit_text(text)
    except: pass

async def upload_progress(current, total, message, start_time, state, title="", topic="", index_no=""):
    now = time.time()
    diff = max(now - start_time, 1)
    if now - state[0] < 15 and current != total: return
    state[0] = now
    percentage = current * 100 / total
    bar = "█" * int(math.floor(percentage / 10)) + "░" * (10 - int(math.floor(percentage / 10)))
    text = f"🚀 **UPLOADING...**\n"
    if index_no: text += f"🔢 **Index:** {index_no}\n"
    text += f"🎬 **Title:** {title[:30]}...\n[{bar}] {percentage:.2f}%\n⚡ **Speed:** {format_bytes(current / diff)}/s"
    await safe_edit(message, text)

async def download_progress(current, total, message, start_time, state, title="", topic="", index_no=""):
    now = time.time()
    diff = max(now - start_time, 1)
    if now - state[0] < 15 and current != total: return
    state[0] = now
    percentage = current * 100 / total
    bar = "█" * int(math.floor(percentage / 10)) + "░" * (10 - int(math.floor(percentage / 10)))
    text = f"📥 **DOWNLOADING...**\n"
    if index_no: text += f"🔢 **Index:** {index_no}\n"
    text += f"🎬 **Title:** {title[:30]}...\n[{bar}] {percentage:.2f}%\n⚡ **Speed:** {format_bytes(current / diff)}/s"
    await safe_edit(message, text)

def beautify_caption(text):
    if not text: return ""
    text = re.sub(r"(?i)\n*Index\s*:", "Index:", text)
    text = re.sub(r"(?i)\n*Title\s*:", "\n\nTitle:", text)
    text = re.sub(r"(?i)\n*Topic\s*:", "\n\nTopic:", text)
    text = re.sub(r"(?i)\n*Batch\s*:", "\n\nBatch:", text)
    text = re.sub(r"(?i)\n*Extracted By\s*:", "\n\nExtracted By:", text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text

# 🟢 DYNAMIC FONT & COLOR WATERMARK ENGINE
async def generate_thumbnail(video_path, watermark="", font_file="default.ttf", font_color="white"):
    if not video_path or not os.path.exists(video_path): return None
    if not Image: return None
    thumb_path = f"{video_path}_thumb.jpg"
    
    cmd = ["ffmpeg", "-i", video_path, "-ss", "00:00:01", "-vframes", "1", "-y", thumb_path, "-loglevel", "quiet"]
    proc = await asyncio.create_subprocess_exec(*cmd)
    await proc.wait()

    if not os.path.exists(thumb_path): return None
    if watermark and watermark.lower() != "skip":
        try:
            def apply_pil_watermark():
                img = Image.open(thumb_path).convert("RGBA")
                draw = ImageDraw.Draw(img)
                try:
                    font_size = int(img.width / 12)
                    # 🟢 Loads font from the 'fonts/' directory dynamically
                    actual_font_path = os.path.join(FONT_DIR, font_file)
                    font = ImageFont.truetype(actual_font_path, font_size)
                except IOError:
                    font = ImageFont.load_default()
                
                bbox = draw.textbbox((0, 0), watermark, font=font)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                x, y = (img.width - w) / 2, (img.height - h) / 2
                
                pad = int(img.width/50)
                draw.rectangle([x-pad, y-pad, x+w+pad, y+h+pad], fill=(0,0,0,150))
                
                # Dark Outline/Shadow for contrast
                shadow_color = "black" if font_color != "black" else "white"
                for dx in [-2, 0, 2]:
                    for dy in [-2, 0, 2]:
                        draw.text((x+dx, y+dy), watermark, font=font, fill=shadow_color)
                        
                # Dynamic Selected Color
                draw.text((x, y), watermark, font=font, fill=font_color)
                img.convert('RGB').save(thumb_path, "JPEG", quality=95)

            await asyncio.to_thread(apply_pil_watermark)
        except Exception as e: print(f"Watermark Error: {e}")
    return thumb_path

# ==========================================
# COMMANDS
# ==========================================
@app.on_message(filters.command(["start", "help"]) & filters.private)
async def start_cmd(client, message):
    await users_col.update_one({"_id": message.from_user.id}, {"$set": {"state": "idle"}}, upsert=True)
    if await check_access(message.from_user.id):
        text = (
            f"⚡️ **𝗪𝗘𝗟𝗖𝗢𝗠𝗘 𝗧𝗢 𝗠𝟯𝗨𝟴 𝗣𝗥𝗢** ⚡️\n\n"
            "🔹 `/loginsrc` ➜ Connect Extractor\n"
            "🔹 `/loginup` ➜ Connect Uploader\n"
            "🔹 `/settings` ➜ 🎨 Thumbnail Fonts & Colors\n"
            "🔹 `/watermark` ➜ Default Text\n"
            "🔹 `/src` ➜ Advanced Clone\n"
            "🔹 `/id` ➜ Get User/Chat ID\n"
        )
        await message.reply(text)

@app.on_message(filters.command("id"))
async def get_id_cmd(client, message):
    text = f"🆔 **Current Chat ID:** `{message.chat.id}`\n"
    if message.reply_to_message:
        if message.reply_to_message.forward_from_chat: 
            text += f"📢 **Forwarded Chat ID:** `{message.reply_to_message.forward_from_chat.id}`\n"
        elif message.reply_to_message.forward_from: 
            text += f"👤 **Forwarded User ID:** `{message.reply_to_message.forward_from.id}`\n"
    await message.reply(text)

@app.on_message(filters.command("watermark") & filters.private)
async def watermark_cmd(client, message):
    if len(message.command) < 2: return await message.reply("❌ Use: `/watermark YourName`")
    wm_text = message.text.split(None, 1)[1]
    await users_col.update_one({"_id": message.from_user.id}, {"$set": {"watermark": wm_text}}, upsert=True)
    await message.reply(f"✅ **Default Watermark Saved:** {wm_text}")

@app.on_message(filters.command("src") & filters.private)
async def src_cmd(client, message):
    if not await check_access(message.from_user.id): return
    await users_col.update_one({"_id": message.from_user.id}, {"$set": {"state": "waiting_for_src_link"}})
    await message.reply("🔗 Send **Message Link** (Source message).")

# ==========================================
# MAIN LOGIC (State Machine)
# ==========================================
@app.on_message(filters.text & filters.private & ~filters.command(["start", "settings", "id", "watermark", "src"]))
async def handle_steps(client, message):
    user_id = message.from_user.id
    if not await check_access(user_id): return
    user = await users_col.find_one({"_id": user_id})
    if not user: return
    state = user.get("state")
    text = message.text.strip()
    
    if state == "waiting_for_src_link":
        if "t.me/" not in text: return await message.reply("❌ Invalid Link!")
        await users_col.update_one({"_id": user_id}, {"$set": {"state": "waiting_for_src_remove", "src_link": text}})
        await message.reply("🧹 **Word Removal System**\nWords to delete? (Comma separated, `/d` for none)")

    elif state == "waiting_for_src_remove":
        remove_list = [w.strip() for w in text.split(",")] if text != "/d" else []
        await users_col.update_one({"_id": user_id}, {"$set": {"state": "waiting_for_src_caption", "src_remove": remove_list}})
        await message.reply("📝 **Replace Mode**\n`Old:New` format (`/d` for none)")

    elif state == "waiting_for_src_caption":
        replace_dict = {}
        if text != "/d":
            for p in text.split("|"): 
                old, new = p.split(":")
                replace_dict[old.strip()] = new.strip()
        await users_col.update_one({"_id": user_id}, {"$set": {"state": "waiting_for_src_watermark", "src_replace": replace_dict}})
        wm_def = user.get("watermark", "No Watermark")
        await message.reply(f"©️ **Watermark Name?**\n(`/d` for `{wm_def}`)")

    elif state == "waiting_for_src_watermark":
        wm_text = user.get("watermark", "") if text == "/d" else text
        await users_col.update_one({"_id": user_id}, {"$set": {"state": "waiting_for_src_target", "temp_wm": wm_text}})
        await message.reply("📢 **Target Link ya ID?** (`/d` for Here)")

    elif state == "waiting_for_src_target":
        await users_col.update_one({"_id": user_id}, {"$set": {"state": "idle"}})
        
        # 🟢 FETCH USER FONT/COLOR SETTINGS FROM DATABASE
        font_file = user.get("thumb_font", "default.ttf")
        font_color = user.get("thumb_color", "white")
        wm_text = user.get("temp_wm", "")
        
        await message.reply(f"🔄 **Processing Started...**\n*(Thumbnail Settings Applied: {AVAILABLE_COLORS.get(font_color, font_color).upper()} color with {AVAILABLE_FONTS.get(font_file, font_file)} font)*")
        
        # Yahan jab upload/download process chale, aap thumbnail function ko naye parameters ke sath call karenge:
        # thumb_path = await generate_thumbnail(file_path, wm_text, font_file, font_color)
        
        await message.reply("✅ Process execution logic connect kijiye jaise batch.py me tha!")

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    print("🤖 Enterprise Bot Running with 100+ Colors UI...", flush=True)
    app.run()
