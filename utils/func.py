import concurrent.futures
import time
import os
import re
import yt_dlp
import cv2
import logging
import asyncio
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_DB as MONGO_URI, DB_NAME

# 🟢 Pillow Library for Advanced Thumbnail Font Watermarking
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image, ImageDraw, ImageFont = None, None, None
    print("⚠️ Pillow not installed! Run 'pip install Pillow'")

try:
    from theme_config import FONT_DIR
except ImportError:
    FONT_DIR = "fonts"

# GLOBAL VARIABLE FOR HUMAN SLEEP CYCLE
IS_PAUSED = False

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

PUBLIC_LINK_PATTERN = re.compile(r'(https?://)?(t\.me|telegram\.me)/([^/]+)(/(\d+))?')
PRIVATE_LINK_PATTERN = re.compile(r'(https?://)?(t\.me|telegram\.me)/c/(\d+)(/(\d+))?')
VIDEO_EXTENSIONS = {"mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "mpeg", "mpg", "3gp"}

# Connection pooling jisse bot DB ko baar-baar open/close na kare
mongo_client = AsyncIOMotorClient(MONGO_URI, maxPoolSize=50, minPoolSize=10, maxIdleTimeMS=10000)
db = mongo_client[DB_NAME]
users_collection = db["users"]
premium_users_collection = db["premium_users"]
statistics_collection = db["statistics"]
codedb = db["redeem_code"]
admin_auth_collection = db["admin_auth"]
admin_logs_collection = db["admin_logs"]

# ------- < start > Session Encoder don't change -------

a1 = "SDRSX1NSQ19ib3Q="
a2 = "Mw=="
a3 = "Z2V0X21lc3NhZ2Vz" 
a4 = "cmVwbHlfcGhvdG8=" 
a5 = "c3RhcnQ="
attr1 = "cGhvdG8="
attr2 = "ZmlsZV9pZA=="
a7 = "8J+RiyBXZWxjb21lIHRvIHRoZSBFbGl0ZSBINFIgRXh0cmFjdGlvbiBab25lISDimqEKCkkgYW0gdGhlIG1vc3QgYWR2YW5jZWQgYm90IGRlc2lnbmVkIHRvIGJ5cGFzcyByZXN0cmljdGlvbnMgYW5kIHNhdmUgeW91ciBwcmVtaXVtIGNvbnRlbnQuCgpNeSBTdXBlcnBvd2VyczoK4pyFIEV4dHJhY3QgcmVzdHJpY3RlZCBtZWRpYSBmcm9tIEFOWSBUZWxlZ3JhbSBDaGFubmVsIG9yIEdyb3VwLgrimIUgRG93bmxvYWQgdWx0cmEtZmFzdCBtZWRpYSBmcm9tIFlvdVR1YmUsIEluc3RhZ3JhbSwgYW5kIFZJUCBwbGF0Zm9ybXMuCgpIb3cgdG8gY29tbWFuZCBtZToKU2ltcGx5IGRyb3AgYSBwdWJsaWMgbGluayB0byB3aXRuZXNzIHRoZSBtYWdpYy4gRm9yIHByaXZhdGUgZm9ydHJlc3Nlcywgc2VuZCAvbG9naW4uCgpFbmdpbmVlcmVkICYgUG93ZXJlZCBieSB0aGUgbGVnZW5kYXJ5IEg0Ug=="
a8 = "Sm9pbiBINFIgVXBkYXRlcw=="
a9 = "Q29udGFjdCBCb3NzIChINFIp" 
a10 = "aHR0cHM6Ly90Lm1lL0g0Ul9TUkNfYm90" 
a11 = "aHR0cHM6Ly90Lm1lL0g0Ul9Db250YWN0X2JvdA==" 

# ------- < end > Session Encoder don't change --------

# 🟢 CAPTION BEAUTIFIER
def beautify_caption(text):
    if not text: return ""
    
    # Existing emojis ko clean karo taaki output me duplicate na ho
    text = re.sub(r'[🎬📁🏷️👤🖥️📦🔢]', '', text)
    
    # Topic string standardization yahan bhi apply hogi
    text = re.sub(r'(?i)Number Of Digits', 'No. of Digit', text)
    
    replacements = {
        r"(?i)Index\s*:": "\n🔢 **Index:**",
        r"(?i)Title\s*:": "\n🎬 **Title:**",
        r"(?i)Topic\s*:": "\n📁 **Topic:**",
        r"(?i)Batch\s*:": "\n🏷️ **Batch:**",
        r"(?i)Extracted By\s*:": "\n👤 **Extracted By:**",
        r"(?i)Quality\s*:": "\n🖥️ **Quality:**",
        r"(?i)Size\s*:": "\n📦 **Size:**"
    }
    for pattern, new_text in replacements.items(): 
        text = re.sub(pattern, new_text, text)
        
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return f"━━━━━━━━━━━━━━━━━━━\n{text}\n━━━━━━━━━━━━━━━━━━━" if text else ""

# 🟢 CUSTOM THUMBNAIL WATERMARKING (TEXT VIA PILLOW)
async def generate_thumbnail(video_path, watermark, user_id):
    if not video_path or not os.path.exists(video_path): 
        return None
    ext = video_path.lower().split('.')[-1]
    if ext not in ['mp4', 'mkv', 'avi', 'mov', 'webm']: 
        return None
    thumb_path = f"{video_path}_thumb.jpg"
    
    cmd = ["ffmpeg", "-i", video_path, "-ss", "00:00:01", "-vframes", "1", "-y", thumb_path, "-loglevel", "quiet"]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()
    except Exception as e:
        print(f"Thumb extraction error: {e}")
        return None

    if not os.path.exists(thumb_path):
        return None

    if watermark and watermark.lower() != "skip" and Image:
        font_file = await get_user_data_key(user_id, "thumb_font", "default.ttf")
        font_color = await get_user_data_key(user_id, "thumb_color", "white")
        
        try:
            def apply_pil_watermark():
                img = Image.open(thumb_path).convert("RGBA")
                draw = ImageDraw.Draw(img)
                try:
                    font_size = int(img.width / 12)
                    actual_font_path = os.path.join(FONT_DIR, font_file)
                    font = ImageFont.truetype(actual_font_path, font_size)
                except IOError:
                    font = ImageFont.load_default()
                
                bbox = draw.textbbox((0, 0), watermark, font=font)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                x, y = (img.width - w) / 2, (img.height - h) / 2
                
                pad = int(img.width/50)
                draw.rectangle([x-pad, y-pad, x+w+pad, y+h+pad], fill=(0,0,0,150))
                
                shadow_color = "black" if font_color != "black" else "white"
                for dx in [-2, 0, 2]:
                    for dy in [-2, 0, 2]:
                        draw.text((x+dx, y+dy), watermark, font=font, fill=shadow_color)
                        
                draw.text((x, y), watermark, font=font, fill=font_color)
                img.convert('RGB').save(thumb_path, "JPEG", quality=95)

            await asyncio.to_thread(apply_pil_watermark)
        except Exception as e:
            print(f"Pillow Watermarking Error: {e}")
            
    return thumb_path

def is_private_link(link):
    return bool(PRIVATE_LINK_PATTERN.match(link))

def thumbnail(sender):
    return f'{sender}.jpg' if os.path.exists(f'{sender}.jpg') else None

def hhmmss(seconds):
    return time.strftime('%H:%M:%S', time.gmtime(seconds))

def E(L):   
    private_match = re.match(r'https://t\.me/c/(\d+)/(?:\d+/)?(\d+)', L)
    public_match = re.match(r'https://t\.me/([^/]+)/(?:\d+/)?(\d+)', L)
    
    if private_match:
        return f'-100{private_match.group(1)}', int(private_match.group(2)), 'private'
    elif public_match:
        return public_match.group(1), int(public_match.group(2)), 'public'
    
    return None, None, None

def get_display_name(user):
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    elif user.first_name:
        return user.first_name
    elif user.last_name:
        return user.last_name
    elif user.username:
        return user.username
    else:
        return "Unknown User"

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def get_dummy_filename(info):
    file_type = info.get("type", "file")
    extension = {
        "video": "mp4",
        "photo": "jpg",
        "document": "pdf",
        "audio": "mp3"
    }.get(file_type, "bin")
    
    return f"downloaded_file_{int(time.time())}.{extension}"

async def is_private_chat(event):
    return event.is_private

async def save_user_data(user_id, key, value):
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {key: value}},
        upsert=True
    )

async def download_youtube_video(url, uid):
    """
    YT-DLP ka use karke background me video download karega.
    Database se user ki cookies nikal kar use karega.
    """
    from utils.db import get_user_cookie
    cookie_file = f"yt_cookies_{uid}.txt"
    
    # DB se user ki cookies nikalna
    cookies = await get_user_cookie(uid, "yt")
            
    if cookies:
        # Yahan encoding="utf-8" add kiya gaya hai
        with open(cookie_file, "w", encoding="utf-8") as f:
            f.write(cookies)
            
    try:
        def _dl():
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'merge_output_format': 'mp4',
                'outtmpl': f'yt_download_{uid}_%(id)s.%(ext)s',
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,  # Add kiya
                'legacyserverconnect': True  # Add kiya
            }
            if os.path.exists(cookie_file):
                ydl_opts['cookiefile'] = cookie_file
                
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                # Handle possible extension change after post-processing
                base, _ = os.path.splitext(filename)
                for ext in ['.mp4', '.mkv', '.webm']:
                    if os.path.exists(base + ext):
                        return base + ext
                return filename
                
        # Main event loop block na ho isliye isko alag thread me bhejo
        file_path = await asyncio.to_thread(_dl)
        return file_path
        
    except Exception as e:
        logger.error(f"❌ YouTube Download Error: {e}")
        return None
    finally:
        # Cache clean karna zaroori hai
        if os.path.exists(cookie_file):
            try: os.remove(cookie_file)
            except: pass

async def copy_header_and_repair(corrupt_file, reference_file):
    """Untrunc ka use karke good video ka header corrupt video me inject karega"""
    if not os.path.exists(corrupt_file) or not os.path.exists(reference_file):
        return None
        
    logger.info(f"🛠 Fixing Corrupted Video using reference header: {reference_file}")
    fixed_file = f"{corrupt_file}_fixed.mp4"
    
    try:
        # untrunc command execute hogi
        proc = await asyncio.create_subprocess_exec(
            "untrunc", reference_file, corrupt_file,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.wait()
        
        # Agar repair successful raha toh purani corrupt file delete karke fixed file return karega
        if os.path.exists(fixed_file) and os.path.getsize(fixed_file) > 1024:
            os.remove(corrupt_file)
            os.rename(fixed_file, corrupt_file)
            return corrupt_file
        else:
            return None
    except Exception as e:
        logger.error(f"❌ Header Copy Repair Failed: {e}")
        return None

async def get_user_data_key(user_id, key, default=None):
    user_data = await users_collection.find_one({"user_id": int(user_id)})
    return user_data.get(key, default) if user_data else default

async def get_user_data(user_id):
    try:
        user_data = await users_collection.find_one({"user_id": user_id})
        return user_data
    except Exception as e:
        return None

async def save_user_session(user_id, session_string):
    try:
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "session_string": session_string,
                "updated_at": datetime.now()
            }},
            upsert=True
        )
        logger.info(f"Saved session for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving session for user {user_id}: {e}")
        return False

async def remove_user_session(user_id):
    try:
        await users_collection.update_one(
            {"user_id": user_id},
            {"$unset": {"session_string": ""}}
        )
        logger.info(f"Removed session for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing session for user {user_id}: {e}")
        return False

async def save_user_bot(user_id, bot_token):
    try:
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "bot_token": bot_token,
                "updated_at": datetime.now()
            }},
            upsert=True
        )
        logger.info(f"Saved bot token for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving bot token for user {user_id}: {e}")
        return False

async def remove_user_bot(user_id):
    try:
        await users_collection.update_one(
            {"user_id": user_id},
            {"$unset": {"bot_token": ""}}
        )
        logger.info(f"Removed bot token for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing bot token for user {user_id}: {e}")
        return False

# 🟢 CASE-INSENSITIVE CAPTION WORD REMOVAL
async def process_text_with_rules(user_id, text):
    if not text:
        return ""
    
    try:
        replacements = await get_user_data_key(user_id, "replacement_words", {})
        delete_words = await get_user_data_key(user_id, "delete_words", [])
        
        processed_text = text
        for word, replacement in replacements.items():
            processed_text = re.sub(re.escape(word), replacement, processed_text, flags=re.IGNORECASE)
        
        if delete_words:
            for word in delete_words:
                processed_text = re.sub(re.escape(word), "", processed_text, flags=re.IGNORECASE)
            processed_text = " ".join(processed_text.split())
        
        return processed_text
    except Exception as e:
        logger.error(f"Error processing text with rules: {e}")
        return text

async def screenshot(video: str, duration: int, sender: str) -> str | None:
    existing_screenshot = f"{sender}.jpg"
    if os.path.exists(existing_screenshot):
        return existing_screenshot

    time_stamp = hhmmss(duration // 2)
    output_file = datetime.now().isoformat("_", "seconds") + ".jpg"

    cmd = [
        "ffmpeg",
        "-ss", time_stamp,
        "-i", video,
        "-frames:v", "1",
        output_file,
        "-y"
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()

    if os.path.isfile(output_file):
        return output_file
    else:
        print(f"FFmpeg Error: {stderr.decode().strip()}")
        return None

async def get_video_metadata(file_path):
    default_values = {'width': 1, 'height': 1, 'duration': 1}
    loop = asyncio.get_event_loop()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    
    try:
        def _extract_metadata():
            try:
                vcap = cv2.VideoCapture(file_path)
                if not vcap.isOpened():
                    return default_values

                width = round(vcap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = round(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = vcap.get(cv2.CAP_PROP_FPS)
                frame_count = vcap.get(cv2.CAP_PROP_FRAME_COUNT)

                if fps <= 0:
                    return default_values

                duration = round(frame_count / fps)
                if duration <= 0:
                    return default_values

                vcap.release()
                return {'width': width, 'height': height, 'duration': duration}
            except Exception as e:
                logger.error(f"Error in video_metadata: {e}")
                return default_values
        
        return await loop.run_in_executor(executor, _extract_metadata)
        
    except Exception as e:
        logger.error(f"Error in get_video_metadata: {e}")
        return default_values

async def add_premium_user(user_id, duration_value, duration_unit):
    try:
        now = datetime.now()
        expiry_date = None
        
        if duration_unit == "min":
            expiry_date = now + timedelta(minutes=duration_value)
        elif duration_unit == "hours":
            expiry_date = now + timedelta(hours=duration_value)
        elif duration_unit == "days":
            expiry_date = now + timedelta(days=duration_value)
        elif duration_unit == "weeks":
            expiry_date = now + timedelta(weeks=duration_value)
        elif duration_unit == "month":
            expiry_date = now + timedelta(days=30 * duration_value)
        elif duration_unit == "year":
            expiry_date = now + timedelta(days=365 * duration_value)
        elif duration_unit == "decades":
            expiry_date = now + timedelta(days=3650 * duration_value)
        else:
            return False, "Invalid duration unit"
            
        await premium_users_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "subscription_start": now,
                "subscription_end": expiry_date,
                "expireAt": expiry_date
            }},
            upsert=True
        )
        
        await premium_users_collection.create_index("expireAt", expireAfterSeconds=0)
        
        return True, expiry_date
    except Exception as e:
        logger.error(f"Error adding premium user {user_id}: {e}")
        return False, str(e)

async def is_premium_user(user_id):
    try:
        user = await premium_users_collection.find_one({"user_id": user_id})
        if user and "subscription_end" in user:
            now = datetime.now()
            return now < user["subscription_end"]
        return False
    except Exception as e:
        logger.error(f"Error checking premium status for {user_id}: {e}")
        return False

async def get_premium_details(user_id):
    try:
        user = await premium_users_collection.find_one({"user_id": user_id})
        if user and "subscription_end" in user:
            return user
        return None
    except Exception as e:
        logger.error(f"Error getting premium details for {user_id}: {e}")
        return None

async def log_admin_activity(admin_id, admin_name, action, target="N/A"):
    """Admin ki har activity ko database me save karega"""
    try:
        await admin_logs_collection.insert_one({
            "admin_id": admin_id,
            "admin_name": admin_name,
            "action": action,
            "target": target,
            "timestamp": datetime.now()
        })
    except Exception as e:
        logger.error(f"Activity log error: {e}")
