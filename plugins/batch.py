import os, re, time, asyncio, json, logging
import random
import aiofiles
import shutil
from utils.func import db
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import UserNotParticipant, FloodWait
from config import API_ID, API_HASH, STRING, FORCE_SUB, FREEMIUM_LIMIT, PREMIUM_LIMIT, MONGO_DB, DB_NAME
import utils.func as global_state  # Direct reference state
from utils.func import get_user_data, screenshot, thumbnail, get_video_metadata, save_user_data
import utils.func as global_state
from utils.func import get_user_data_key, process_text_with_rules, is_premium_user, E, log_admin_activity, get_display_name
from utils.func import generate_thumbnail, beautify_caption
from shared_client import app as X
from plugins.settings import rename_file
from plugins.start import subscribe as sub
from utils.custom_filters import login_in_progress
from utils.encrypt import dcs
from typing import Dict, Any, Optional
from utils.func import copy_header_and_repair

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger("pyrogram.session.session").setLevel(logging.ERROR)

Y = None if not STRING else __import__('shared_client').userbot
Z, P, UB, UC = {}, {}, {}, {}

ACTIVE_USERS = {}
ACTIVE_USERS_FILE = "active_users.json"
LAST_UPDATE_TIME = {}

try:
    # Ab hum global db connection use kar rahe hain, direct func.py se
    cache_col = db["file_cache"]
    logger.info("✅ MongoDB File Cache connected from global pool!")
except Exception as e:
    cache_col = None
    logger.warning("⚠️ MongoDB caching disabled.")

def load_active_users():
    try:
        if os.path.exists(ACTIVE_USERS_FILE):
            with open(ACTIVE_USERS_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception:
        return {}

async def save_active_users_to_file():
    try:
        async with aiofiles.open(ACTIVE_USERS_FILE, 'w') as f:
            await f.write(json.dumps(ACTIVE_USERS))
    except Exception as e:
            # Ab ye NameError nahi dega
            print(f"⚠️ Failed to save active users file: {e}")

async def add_active_batch(user_id: int, batch_info: Dict[str, Any]):
    ACTIVE_USERS[str(user_id)] = batch_info
    await save_active_users_to_file()

def is_user_active(user_id: int) -> bool:
    return str(user_id) in ACTIVE_USERS

async def update_batch_progress(user_id: int, current: int, success: int):
    if str(user_id) in ACTIVE_USERS:
        ACTIVE_USERS[str(user_id)]["current"] = current
        ACTIVE_USERS[str(user_id)]["success"] = success
        await save_active_users_to_file()

async def request_batch_cancel(user_id: int):
    if str(user_id) in ACTIVE_USERS:
        ACTIVE_USERS[str(user_id)]["cancel_requested"] = True
        await save_active_users_to_file()
        return True
    return False

def should_cancel(user_id: int) -> bool:
    user_str = str(user_id)
    return user_str in ACTIVE_USERS and ACTIVE_USERS[user_str].get("cancel_requested", False)

async def remove_active_batch(user_id: int):
    if str(user_id) in ACTIVE_USERS:
        del ACTIVE_USERS[str(user_id)]
        await save_active_users_to_file()

ACTIVE_USERS = load_active_users()

async def upd_dlg(c):
    try:
        async for _ in c.get_dialogs(limit=100): pass
        return True
    except Exception:
        return False

async def get_msg(c, u, i, d, lt):
    try:
        if lt == 'public':
            try:
                msg = await c.get_messages(i, d)
                if msg and not getattr(msg, "empty", False): return msg
            except FloodWait as fw:
                await asyncio.sleep(fw.value + 5)
                msg = await c.get_messages(i, d)
                if msg and not getattr(msg, "empty", False): return msg
            except Exception: pass
            
            if u:
                try:
                    msg = await u.get_messages(i, d)
                    if msg and not getattr(msg, "empty", False): return msg
                except FloodWait as fw:
                    await asyncio.sleep(fw.value + 5)
                    msg = await u.get_messages(i, d)
                    if msg and not getattr(msg, "empty", False): return msg
                except Exception: pass
            return None
        else:
            if u:
                try:
                    i_str = str(i)
                    targets = []
                    if i_str.lstrip('-').isdigit():
                        base_id = i_str.lstrip('-')
                        targets = [int(f"-100{base_id}"), int(f"-{base_id}"), int(i_str)]
                    else:
                        targets = [i]
                    
                    for target_id in targets:
                        try:
                            result = await u.get_messages(target_id, d)
                            if result and not getattr(result, "empty", False): return result
                        except FloodWait as fw:
                            await asyncio.sleep(fw.value + 5)
                            result = await u.get_messages(target_id, d)
                            if result and not getattr(result, "empty", False): return result
                        except Exception: pass
                    return None
                except Exception: return None
            return None
    except Exception: return None

async def get_ubot(uid):
    bt = await get_user_data_key(uid, "bot_token", None)
    if not bt: return None
    if uid in UB: return UB.get(uid)
    try:
        bot = Client(f"user_{uid}", bot_token=bt, api_id=API_ID, api_hash=API_HASH)
        await bot.start()
        UB[uid] = bot
        return bot
    except Exception: return None

async def get_uclient(uid):
    ud = await get_user_data(uid)
    ubot = UB.get(uid)
    cl = UC.get(uid)
    if cl:
        if not cl.is_connected:
            try: await cl.connect()
            except: pass
        return cl
    if not ud: return ubot if ubot else None
    xxx = ud.get('session_string')
    if xxx:
        try:
            ss = dcs(xxx)
            gg = Client(f'{uid}_client', api_id=API_ID, api_hash=API_HASH, device_model="v3saver", session_string=ss)
            await gg.start()
            UC[uid] = gg
            return gg
        except Exception:
            return ubot if ubot else Y
    return Y

async def prog(c, t, C, h, m, st, action="Downloading......."):
    global LAST_UPDATE_TIME
    p = c / t * 100
    now = time.time()
    
    # 🟢 Update time 15 seconds se hata kar 4 seconds kar diya hai (Fast Response)
    if m not in LAST_UPDATE_TIME or (now - LAST_UPDATE_TIME.get(m, 0)) >= 10 or p >= 100:
        LAST_UPDATE_TIME[m] = now
        c_mb = c / (1024 * 1024)
        t_mb = t / (1024 * 1024)
        bar = '🟢' * int(p / 10) + '🔴' * (10 - int(p / 10))
        speed = c / (now - st) / (1024 * 1024) if now > st else 0
        eta = time.strftime('%M:%S', time.gmtime((t - c) / (speed * 1024 * 1024))) if speed > 0 else '00:00'
        
        # 🟢 Action (Downloading/Uploading) text dynamic ho gaya hai
        text = f"__**H4R SRC {action}**__\n\n{bar}\n\n⚡**__Completed__**: {c_mb:.2f} MB / {t_mb:.2f} MB\n📊 **__Done__**: {p:.2f}%\n🚀 **__Speed__**: {speed:.2f} MB/s\n⏳ **__ETA__**: {eta}\n\n**__Powered by H4R__**"
        
        async def safe_edit():
            try: await C.edit_message_text(h, m, text)
            except Exception: pass
                
        asyncio.create_task(safe_edit())
        if p >= 100: LAST_UPDATE_TIME.pop(m, None)

async def send_direct(c, m, tcid, ft=None, rtmid=None):
    try:
        if m.video: await c.send_video(tcid, m.video.file_id, caption=ft, duration=m.video.duration, width=m.video.width, height=m.video.height, reply_to_message_id=rtmid)
        elif m.video_note: await c.send_video_note(tcid, m.video_note.file_id, reply_to_message_id=rtmid)
        elif m.voice: await c.send_voice(tcid, m.voice.file_id, reply_to_message_id=rtmid)
        elif m.sticker: await c.send_sticker(tcid, m.sticker.file_id, reply_to_message_id=rtmid)
        elif m.audio: await c.send_audio(tcid, m.audio.file_id, caption=ft, duration=m.audio.duration, performer=m.audio.performer, title=m.audio.title, reply_to_message_id=rtmid)
        elif m.photo: await c.send_photo(tcid, m.photo.file_id if hasattr(m.photo, 'file_id') else m.photo[-1].file_id, caption=ft, reply_to_message_id=rtmid)
        elif m.document: await c.send_document(tcid, m.document.file_id, caption=ft, file_name=m.document.file_name, reply_to_message_id=rtmid)
        else: return False
        return True
    except FloodWait as fw:
        await asyncio.sleep(fw.value + 2)
        return False
    except Exception:
        return False

async def safe_status_edit(client, chat_id, msg_id, text):
    try: await client.edit_message_text(chat_id, msg_id, text)
    except Exception: pass

async def process_msg(c, u, m, d, lt, uid, i, task=None):
    if isinstance(d, str):
        try: d = int(d)
        except Exception: pass

    tcid = d
    rtmid = None

    try:
        # Yahan exactly 8 spaces ki indentation honi chahiye (def se)
        orig_text = m.caption.markdown if m.caption else (m.text.markdown if m.text else '')

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 🟢 SMART YOUTUBE INTERCEPTION LOGIC
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        yt_match = re.search(r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be)[^\s]+)', orig_text)
        
        if yt_match:
            yt_url = yt_match.group(1)
            cleaned_text = orig_text.replace(yt_url, '').strip()
            
            proc_text = await process_text_with_rules(uid, cleaned_text)
            user_cap = await get_user_data_key(uid, 'caption', '')
            raw_caption = f'{proc_text}\n\n{user_cap}' if proc_text and user_cap else user_cap if user_cap else proc_text
            
            if task:
                for word in task.get("remove_list", []): raw_caption = re.sub(re.escape(word), "", raw_caption, flags=re.IGNORECASE)
                for old, new in task.get("replace_dict", {}).items(): raw_caption = re.sub(re.escape(old), new, raw_caption, flags=re.IGNORECASE)
            
            raw_caption = re.sub(r'(?i)Number Of Digits', 'No. of Digit', raw_caption)
            
            if not ("🎬 Title:" in raw_caption or "📁 Topic:" in raw_caption):
                ft = beautify_caption(raw_caption)
            else:
                ft = raw_caption.strip()

            p = await c.send_message(uid, '📥 YouTube Link Detected! Private video extract kar raha hu...')
            
            from utils.func import download_youtube_video
            yt_file = await download_youtube_video(yt_url, uid)
            
            if yt_file and os.path.exists(yt_file):
                await safe_status_edit(c, uid, p.id, '📤 Uploading YouTube Video to Target Chat...')
                # Yahan `generate_thumbnail` ko call karne se pehle zaroori parameters pass hone chahiye
                th = await generate_thumbnail(yt_file, task.get("watermark", "") if task else "", uid)
                mtd = await get_video_metadata(yt_file)
                
                try:
                    await c.send_video(
                        tcid, video=yt_file, caption=ft, thumb=th, 
                        width=mtd['width'], height=mtd['height'], duration=mtd['duration'], 
                        reply_to_message_id=rtmid,
                        progress=prog, progress_args=(c, uid, p.id, time.time(), "Uploading YT Video...")
                    )
                except FloodWait as fw:
                    await safe_status_edit(c, uid, p.id, f'⚠️ FloodWait: Telegram blocked upload for {fw.value}s...')
                    await asyncio.sleep(fw.value + 5)
                except Exception as e:
                    logger.error(f"Failed to upload YT video: {e}")
                    
                if os.path.exists(yt_file): os.remove(yt_file)
                await c.delete_messages(uid, p.id)
                return 'Done (YouTube)'
            else:
                await safe_status_edit(c, uid, p.id, '❌ YouTube Download Failed. Skipping YT, forwarding normal text instead.')
                await asyncio.sleep(2)
                await c.delete_messages(uid, p.id)
                orig_text = cleaned_text
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # 🟢 NORMAL TELEGRAM EXTRACTION LOGIC CONTINUES BELOW...
        if m.media:
            # ... (yahan se tumhara purana m.media wala code shuru hoga)

    try:
        if m.media:
            orig_text = m.caption.markdown if m.caption else ''
            proc_text = await process_text_with_rules(uid, orig_text)
            user_cap = await get_user_data_key(uid, 'caption', '')
            raw_caption = f'{proc_text}\n\n{user_cap}' if proc_text and user_cap else user_cap if user_cap else proc_text
            
            if task:
                for word in task.get("remove_list", []): raw_caption = re.sub(re.escape(word), "", raw_caption, flags=re.IGNORECASE)
                for old, new in task.get("replace_dict", {}).items(): raw_caption = re.sub(re.escape(old), new, raw_caption, flags=re.IGNORECASE)
            
            raw_caption = re.sub(r'\.(mp4|mkv|pdf|avi|webm|jpg|png)', '', raw_caption, flags=re.IGNORECASE)
            
            # 🟢 SMART CAPTION CHECK: Agar pehle se formatted hai, toh chhed-chhaad mat karo!
            if "🎬 Title:" in raw_caption or "📁 Topic:" in raw_caption or "🎬" in raw_caption:
                ft = raw_caption.strip()
            else:
                ft = beautify_caption(raw_caption)
            is_restricted = getattr(m.chat, "has_protected_content", False)
            
            if lt == 'public' and not is_restricted:
                success = await send_direct(c, m, tcid, ft, rtmid)
                if success: return 'Sent directly.'
            
            p = await c.send_message(uid, '⏳ Initializing...')
            
            forward_mode = await get_user_data_key(uid, "forward_mode", False)
            if forward_mode and not is_restricted:
                try:
                    client_to_use = getattr(m, '_client', u if u else c)
                    await client_to_use.copy_message(chat_id=tcid, from_chat_id=m.chat.id, message_id=m.id, caption=ft if ft else None, reply_to_message_id=rtmid)
                    await c.delete_messages(uid, p.id)
                    return 'Fast Forwarded ✅'
                except FloodWait as fw:
                    await asyncio.sleep(fw.value + 5)
                except Exception as e:
                    await asyncio.sleep(3)
            
            st = time.time()
            await safe_status_edit(c, uid, p.id, '⬇️ Downloading...')

            c_name = f"{time.time()}"
            original_ext = ""
            if m.video: original_ext = ".mp4"; c_name = f"{time.time()}.mp4"
            elif m.audio: original_ext = ".mp3"; c_name = f"{time.time()}.mp3"
            elif m.document: 
                original_ext = os.path.splitext(m.document.file_name)[1].lower() if m.document.file_name else ".pdf"
                c_name = f"{time.time()}{original_ext}"
            elif m.photo: original_ext = ".jpg"; c_name = f"{time.time()}.jpg"
    
            try:
                client_to_use = getattr(m, '_client', u if u else c)
                f = await client_to_use.download_media(m, file_name=c_name, progress=prog, progress_args=(c, uid, p.id, st, "Downloading......."))
            except FloodWait as fw:
                await safe_status_edit(c, uid, p.id, f"⚠️ FloodWait: Sleeping for {fw.value} seconds.")
                await asyncio.sleep(fw.value + 5)
                f = None
            except Exception:
                f = None
                
            if not f:
                await safe_status_edit(c, uid, p.id, 'Failed.')
                return 'Failed.'
            
            await safe_status_edit(c, uid, p.id, 'Renaming...')
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 🟢 NEW: CORRUPTION CHECK & HEADER REPAIR LOGIC
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if m.video or (isinstance(f, str) and f.lower().endswith(('.mp4', '.mkv', '.webm'))):
                reference_video_path = f"temp_reference_{uid}.mp4"
                await safe_status_edit(c, uid, p.id, '🔍 Checking video health...')
                
                # Check if video is corrupt using ffprobe
                check_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", f]
                proc = await asyncio.create_subprocess_exec(*check_cmd, stdout=asyncio.subprocess.PIPE)
                stdout, _ = await proc.communicate()
                is_corrupt = not bool(stdout.decode().strip())
                
                if is_corrupt:
                    if os.path.exists(reference_video_path):
                        await safe_status_edit(c, uid, p.id, '🛠 Video Crashed! Copying header from previous good video...')
                        f = await copy_header_and_repair(f, reference_video_path)
                        if not f:
                            await c.delete_messages(uid, p.id)
                            return 'Failed (Unfixable Crash)'
                    else:
                        await safe_status_edit(c, uid, p.id, '❌ Skipped: Video is crashed, but no reference video exists yet.')
                        if os.path.exists(f): os.remove(f)
                        await c.delete_messages(uid, p.id)
                        return 'Failed (No Reference)'
                else:
                    # Agar video completely healthy hai, toh future corrupt videos ke liye isko reference bana lo
                    if not os.path.exists(reference_video_path):
                        shutil.copy2(f, reference_video_path)
                        logger.info("✅ Reference video saved for future header copying.")
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                
                # 1. Filename se specified words delete karo
                if task:
                    for word in task.get("remove_list", []):
                        new_f_name = re.sub(re.escape(word), "", new_f_name, flags=re.IGNORECASE)
                        
                # 2. Topic Normalization (Dono strings ko ek standard format me merge karo)
                new_f_name = re.sub(r'(?i)Number Of Digits', 'No. of Digit', new_f_name)
                
                if original_ext and not new_f_name.lower().endswith(original_ext):
                    new_f_name += original_ext
            
                if new_f_name != renamed_f and os.path.exists(renamed_f):
                    os.rename(renamed_f, new_f_name)
                    f = new_f_name
                else:
                    f = renamed_f
            
            fsize = os.path.getsize(f) / (1024 * 1024 * 1024)
            th = None
            batch_wm = task.get("watermark", "") if task else ""
            
            if m.video or str(f).endswith(('.mp4', '.mkv')):
                 th = await generate_thumbnail(f, batch_wm, uid)
            if not th:
                 th = thumbnail(uid)
            
            if fsize > 2 and Y:
                st = time.time()
                await safe_status_edit(c, uid, p.id, 'File is larger than 2GB. Using alternative method...')
                await upd_dlg(Y)
                mtd = await get_video_metadata(f)
                dur, h, w = mtd['duration'], mtd['width'], mtd['height']
                
                send_funcs = {'video': Y.send_video, 'video_note': Y.send_video_note, 'voice': Y.send_voice, 'audio': Y.send_audio, 'photo': Y.send_photo, 'document': Y.send_document}
                
                try:
                    for mtype, func in send_funcs.items():
                        if f.endswith('.mp4'): mtype = 'video'
                        if getattr(m, mtype, None):
                            # 🟢 UPLOADING TEXT ADDED
                            sent = await func(tcid, f, thumb=th if mtype == 'video' else None, duration=dur if mtype == 'video' else None, height=h if mtype == 'video' else None, width=w if mtype == 'video' else None, caption=ft if m.caption and mtype not in ['video_note', 'voice'] else None, reply_to_message_id=rtmid, progress=prog, progress_args=(c, uid, p.id, st, "Uploading....."))
                            break
                    else:
                        sent = await Y.send_document(tcid, f, thumb=th, caption=ft if m.caption else None, reply_to_message_id=rtmid, progress=prog, progress_args=(c, uid, p.id, st, "Uploading....."))
                except FloodWait as fw:
                    await safe_status_edit(c, uid, p.id, f"⚠️ FloodWait (2GB+): Sleeping for {fw.value}s...")
                    await asyncio.sleep(fw.value + 5)
                    os.remove(f)
                    return 'Failed (FloodWait).'
                
                os.remove(f)
                await c.delete_messages(uid, p.id)
                return 'Done (Large file).'
            
            await safe_status_edit(c, uid, p.id, 'Uploading...')
            st = time.time()

            try:
                # 🟢 NORMAL FILES: UPLOADING TEXT ADDED
                if m.video or f.lower().endswith(('.mp4', '.mkv')):
                    mtd = await get_video_metadata(f)
                    await c.send_video(tcid, video=f, caption=ft if m.caption else None, thumb=th, width=mtd['width'], height=mtd['height'], duration=mtd['duration'], progress=prog, progress_args=(c, uid, p.id, st, "Uploading....."), reply_to_message_id=rtmid)
                elif m.document or f.lower().endswith(('.pdf', '.zip', '.apk')):
                    await c.send_document(tcid, document=f, caption=ft if m.caption else None, thumb=th, progress=prog, progress_args=(c, uid, p.id, st, "Uploading....."), reply_to_message_id=rtmid)
                else:
                    await c.send_document(tcid, document=f, caption=ft if m.caption else None, progress=prog, progress_args=(c, uid, p.id, st, "Uploading....."), reply_to_message_id=rtmid)

            except FloodWait as fw:
                await safe_status_edit(c, uid, p.id, f"⚠️ FloodWait: Telegram blocked upload for {fw.value} seconds.")
                await asyncio.sleep(fw.value + 5)
                if os.path.exists(f): os.remove(f)
                return 'Failed (FloodWait).'
            except Exception as e:
                logger.error(f"Upload failed for {f}: {e}")
                await safe_status_edit(c, uid, p.id, f'Upload failed: {str(e)[:30]}')
                if f and os.path.exists(f): 
                    try: os.remove(f)
                    except: pass
                return 'Failed.'
            
            # Safe Cleanup
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except Exception as e:
                    logger.error(f"Failed to safely delete {f}: {e}")
                    
            await c.delete_messages(uid, p.id)
            return 'Done.'
            
        elif m.text:
            orig_text = m.text.markdown
            proc_text = await process_text_with_rules(uid, orig_text)
            user_cap = await get_user_data_key(uid, 'caption', '')
            raw_caption = f'{proc_text}\n\n{user_cap}' if proc_text and user_cap else user_cap if user_cap else proc_text
            
            # 🟢 SMART CAPTION CHECK 
            if "🎬 Title:" in raw_caption or "📁 Topic:" in raw_caption or "🎬" in raw_caption:
                ft = raw_caption.strip()
            else:
                ft = beautify_caption(raw_caption)
            await c.send_message(tcid, text=ft if ft else orig_text, reply_to_message_id=rtmid)
            return 'Sent.'
            
    except Exception as e:
        return f'Error: {str(e)[:50]}'

@X.on_message(filters.command(['batch', 'single']))
async def process_cmd(c, m):
    uid = m.from_user.id
    cmd = m.command[0]
    
    if FREEMIUM_LIMIT == 0 and not await is_premium_user(uid):
        await m.reply_text("This bot does not provide free servies, get subscription from OWNER")
        return
    
    if await sub(c, m) == 1: return
    pro = await m.reply_text('Doing some checks hold on...')
    
    if is_user_active(uid):
        await pro.edit('You have an active task. Use /stop to cancel it.')
        return
    
    ubot = await get_ubot(uid)
    if not ubot:
        await pro.edit('Add your bot with /setbot first')
        return
    
    Z[uid] = {'step': 'start' if cmd == 'batch' else 'start_single'}
    await pro.edit(f'Send {"start link..." if cmd == "batch" else "link you to process"}.')

@X.on_message(filters.command(['cancel', 'stop']))
async def cancel_cmd(c, m):
    uid = m.from_user.id
    if is_user_active(uid):
        if await request_batch_cancel(uid):
            await m.reply_text('Cancellation requested. The current batch will stop after the current download completes.')
        else:
            await m.reply_text('Failed to request cancellation. Please try again.')
    else:
        await m.reply_text('No active batch process found.')

@X.on_message(filters.command("forward"))
async def toggle_forward(c, m):
    uid = m.from_user.id
    current_status = await get_user_data_key(uid, "forward_mode", False)
    new_status = not current_status
    await save_user_data(uid, "forward_mode", new_status)
    if new_status:
        await m.reply_text("✅ **Fast Forward Mode ON**\nAb jin channels me forward ON hoga, bot bina download kiye seedha clone karega!")
    else:
        await m.reply_text("❌ **Fast Forward Mode OFF**\nAb bot sabhi files ko download/upload karega.")

@X.on_message(filters.text & filters.private & ~login_in_progress & ~filters.command([
    'start', 'batch', 'cancel', 'login', 'logout', 'stop', 'set', 
    'pay', 'redeem', 'gencode', 'single', 'generate', 'keyinfo', 'encrypt', 'decrypt', 'keys', 'setbot', 'rembot', 'forward', 'id', 'settings']))
async def text_handler(c, m):
    uid = m.from_user.id
    
    if uid not in Z:
        if m.text and ("t.me/" in m.text or "telegram.me/" in m.text):
            i, d, lt = E(m.text)
            if not i or not d:
                await m.reply_text('❌ Invalid link format.')
                return
            Z[uid] = {'step': 'count', 'cid': i, 'sid': d, 'lt': lt}
            await m.reply_text('🔗 **Starting Link Detected!**\n\nAb aap 2 tarike se bata sakte hain:\n1️⃣ **Ending Link bhejen** (Jahan tak extract karna hai)\n👉 *Ya fir*\n2️⃣ **Number bhejen** (Kitne messages nikalne hain, ex: 50)')
            return
        else:
            return
            
    s = Z[uid].get('step')
    x = await get_ubot(uid)
    if not x:
        await m.reply("Add your bot /setbot `token`")
        return

    if s == 'start':
        L = m.text
        i, d, lt = E(L)
        if not i or not d:
            await m.reply_text('Invalid link format.')
            Z.pop(uid, None)
            return
        Z[uid].update({'step': 'count', 'cid': i, 'sid': d, 'lt': lt})
        await m.reply_text('✅ **Starting Link Saved!**\n\nAb aap 2 tarike se bata sakte hain:\n1️⃣ **Ending Link bhejen** (Jahan tak extract karna hai)\n👉 *Ya fir*\n2️⃣ **Number bhejen** (Kitne messages nikalne hain, ex: 50)')

    elif s == 'start_single':
        L = m.text
        i, d, lt = E(L)
        if not i or not d:
            await m.reply_text('Invalid link format.')
            Z.pop(uid, None)
            return

        Z[uid].update({'step': 'process_single', 'cid': i, 'sid': d, 'lt': lt})
        i, s_id, lt = Z[uid]['cid'], Z[uid]['sid'], Z[uid]['lt']
        pt = await m.reply_text('Processing...')
        
        ubot = UB.get(uid)
        if not ubot:
            await pt.edit('Add bot with /setbot first')
            Z.pop(uid, None)
            return
        
        uc = await get_uclient(uid)
        if not uc:
            await pt.edit('Cannot proceed without user client.')
            Z.pop(uid, None)
            return
            
        if is_user_active(uid):
            await pt.edit('Active task exists. Use /stop first.')
            Z.pop(uid, None)
            return

        try:
            target_chat_id = m.chat.id
            cfg_chat = await get_user_data_key(uid, 'chat_id', None)
            if cfg_chat:
                target_chat_id = int(cfg_chat.split('/')[0]) if '/' in cfg_chat else int(cfg_chat)
                
            try:
                i_str = str(i)
                possible_ids = [i]
                if i_str.lstrip('-').isdigit():
                    base_id = i_str.lstrip('-')
                    possible_ids.extend([int(f"-100{base_id}"), int(f"-{base_id}")])
                
                s_chat = None
                for pid in possible_ids:
                    try:
                        s_chat = await uc.get_chat(pid)
                        if s_chat: break
                    except Exception: pass
                
                source_display = getattr(s_chat, 'title', str(i)) if s_chat else str(i)
            except: 
                source_display = str(i)
                
            try:
                d_chat = await ubot.get_chat(target_chat_id)
                dest_display = getattr(d_chat, 'title', "Private / Bot Chat")
            except: 
                dest_display = str(target_chat_id)

            msg = await get_msg(ubot, uc, i, s_id, lt)
            if msg:
                task_data = {"watermark": await get_user_data_key(uid, "watermark", "")}
                res = await process_msg(ubot, uc, msg, target_chat_id, lt, uid, i, task=task_data)
                await pt.edit(f'1/1: {res}')
                
                if res and isinstance(res, str) and any(x in res for x in ['Done', 'Copied', 'Sent', 'Forwarded', 'Cached']):
                    admin_name = get_display_name(m.from_user)
                    await log_admin_activity(uid, admin_name, "Single File Transferred", f"From: {source_display} ➡️ To: {dest_display}")
            else:
                await pt.edit('⚠️ Message not found! (Private Channel / Removed)')
        except Exception as e:
            await pt.edit(f'Error: {str(e)[:50]}')
        finally:
            Z.pop(uid, None)
            if uid in UC:
                try: await UC[uid].stop()
                except: pass
                UC.pop(uid, None)

    elif s == 'count':
        maxlimit = PREMIUM_LIMIT if await is_premium_user(uid) else FREEMIUM_LIMIT
        
        if m.text.isdigit(): count = int(m.text)
        else:
            end_i, end_d, end_lt = E(m.text)
            if not end_i or not end_d: return await m.reply_text('❌ Please enter a valid number or a valid Telegram ending link.')
            start_d = int(Z[uid]['sid'])
            end_d = int(end_d)
            if str(end_i) != str(Z[uid]['cid']): return await m.reply_text('❌ Ending link usi channel/group ka hona chahiye jiska starting link tha!')
            if end_d < start_d: return await m.reply_text('❌ Ending ID starting ID se bada hona chahiye!')
            count = (end_d - start_d) + 1

        if count > maxlimit: return await m.reply_text(f'❌ Maximum limit is {maxlimit}.')

        # 🟢 STEP 1: WIZARD START
        Z[uid].update({'step': 'ask_remove_words', 'num': count})
        await m.reply_text("📝 **Step 1/4: Words to Remove**\nEnter words you want to remove from caption (comma separated).\n\n🔹 Type `/d` for Default (Settings wale)\n🔹 Type `0` for Previous (Pichle batch wale)")
        return

    elif s == 'ask_remove_words':
        text = m.text.strip()
        Z[uid]['custom_remove'] = "DEFAULT" if text == '/d' else "PREVIOUS" if text == '0' else [w.strip() for w in text.split(',')]
        Z[uid]['step'] = 'ask_replace_words'
        await m.reply_text("🔄 **Step 2/4: Words to Replace**\nEnter words to rename. Format: `old_word | new_word`\n\n🔹 Type `/d` for Default\n🔹 Type `0` for Previous")
        return

    elif s == 'ask_replace_words':
        text = m.text.strip()
        if text == '/d': Z[uid]['custom_replace'] = "DEFAULT"
        elif text == '0': Z[uid]['custom_replace'] = "PREVIOUS"
        else:
            try:
                old_w, new_w = text.split('|')
                Z[uid]['custom_replace'] = {old_w.strip(): new_w.strip()}
            except: Z[uid]['custom_replace'] = {}
            
        Z[uid]['step'] = 'ask_watermark'
        await m.reply_text("🖼️ **Step 3/4: Thumbnail Watermark**\nEnter the text for Video Watermark.\n\n🔹 Type `/d` for Default\n🔹 Type `0` for Previous")
        return

    elif s == 'ask_watermark':
        text = m.text.strip()
        Z[uid]['custom_wm'] = "DEFAULT" if text == '/d' else "PREVIOUS" if text == '0' else text
        Z[uid]['step'] = 'ask_target_chat'
        await m.reply_text("🎯 **Step 4/4: Target Channel ID**\nEnter the Chat ID where you want to send files (e.g., -100123456).\n\n🔹 Type `/d` for Default Chat ID\n🔹 Type `0` for Previous Chat ID")
        return

    elif s == 'ask_target_chat':
        text = m.text.strip()
        Z[uid]['custom_chat'] = "DEFAULT" if text == '/d' else "PREVIOUS" if text == '0' else text
        Z[uid]['step'] = 'process'

        # 🟢 STEP 5: RESOLVING ALL INPUTS & SAVING 'PREVIOUS' DATA
        i, s_id, n, lt = Z[uid]['cid'], Z[uid]['sid'], Z[uid]['num'], Z[uid]['lt']
        success = 0
        pt = await m.reply_text('⚙️ Validating inputs and starting batch...')
        
        uc = await get_uclient(uid)
        ubot = UB.get(uid)
        if not uc or not ubot: return await pt.edit('Missing client setup')
        if is_user_active(uid): return await pt.edit('Active task exists')

        # --- 1. REMOVE WORDS ---
        if Z[uid]['custom_remove'] == "DEFAULT":
            resolved_remove = await get_user_data_key(uid, "delete_words", [])
        elif Z[uid]['custom_remove'] == "PREVIOUS":
            resolved_remove = await get_user_data_key(uid, "last_remove", [])
        else:
            resolved_remove = Z[uid]['custom_remove']
            await save_user_data(uid, "last_remove", resolved_remove) # Naya hai toh future ke liye save kar lo

        # --- 2. REPLACE WORDS ---
        if Z[uid]['custom_replace'] == "DEFAULT":
            resolved_replace = await get_user_data_key(uid, "replacement_words", {})
        elif Z[uid]['custom_replace'] == "PREVIOUS":
            resolved_replace = await get_user_data_key(uid, "last_replace", {})
        else:
            resolved_replace = Z[uid]['custom_replace']
            await save_user_data(uid, "last_replace", resolved_replace)

        # --- 3. WATERMARK ---
        if Z[uid]['custom_wm'] == "DEFAULT":
            resolved_wm = await get_user_data_key(uid, "watermark", "")
        elif Z[uid]['custom_wm'] == "PREVIOUS":
            resolved_wm = await get_user_data_key(uid, "last_wm", "")
        else:
            resolved_wm = Z[uid]['custom_wm']
            await save_user_data(uid, "last_wm", resolved_wm)

        # --- 4. TARGET CHAT ---
        if Z[uid]['custom_chat'] == "DEFAULT":
            cfg_chat = await get_user_data_key(uid, 'chat_id', None)
            if cfg_chat: 
                target_chat_id = int(cfg_chat.split('/')[0]) if '/' in cfg_chat else int(cfg_chat)
            else:
                target_chat_id = m.chat.id
        elif Z[uid]['custom_chat'] == "PREVIOUS":
            last_chat = await get_user_data_key(uid, "last_chat", m.chat.id)
            target_chat_id = int(last_chat)
        else:
            try: 
                target_chat_id = int(Z[uid]['custom_chat'])
                await save_user_data(uid, "last_chat", target_chat_id)
            except:
                target_chat_id = m.chat.id

        # Package task data
        task_data = {
            "remove_list": resolved_remove,
            "replace_dict": resolved_replace,
            "watermark": resolved_wm
        }

        # --- 🟢 FINALLY PROCESSING THE BATCH ---
        await add_active_batch(uid, {
            "total": n, "current": 0, "success": 0,
            "source": str(i), "destination": str(target_chat_id),
            "cancel_requested": False, "progress_message_id": pt.id
        })
        
        try:
            batch_start_time = time.time()
            for j in range(n):
                # 🟢 Smart Break (Anti-ban)
                if time.time() - batch_start_time > 10800:
                    break_dur = random.uniform(1150.5, 1250.2)
                    try: await pt.edit(f'💤 Anti-Ban: Lagatar 3 ghante se extract ho raha hai. Account safe rakhne ke liye {int(break_dur/60)} min ka break le raha hu...')
                    except: pass
                    await asyncio.sleep(break_dur)
                    batch_start_time = time.time()
                
                if should_cancel(uid):
                    await pt.edit(f'Cancelled at {j}/{n}. Success: {success}')
                    break
                
                await update_batch_progress(uid, j, success)
                mid = int(s_id) + j
                
                try:
                    msg = await get_msg(ubot, uc, i, mid, lt)
                    if msg:
                        res = await process_msg(ubot, uc, msg, target_chat_id, lt, uid, i, task=task_data)
                        if res and isinstance(res, str) and any(x in res for x in ['Done', 'Copied', 'Sent', 'Forwarded']):
                            success += 1
                    else:
                        try: await pt.edit(f"⚠️ Skipped {mid}: Not found.")
                        except: pass
                except Exception as e:
                    try: await pt.edit(f'{j+1}/{n}: Error - {str(e)[:30]}')
                    except: pass
                
                if n > 1:
                    delay_time = random.uniform(17.5, 35.8)
                    try: await pt.edit(f'Sleeping for {delay_time:.2f}s to act like human...')
                    except: pass
                    await asyncio.sleep(delay_time)
            
            if j + 1 == n:
                await m.reply_text(f'✅ Batch Completed!\n📊 Successfully Processed: {success}/{n}\n🎯 Sent to Chat ID: `{target_chat_id}`')
                
        finally:
            await remove_active_batch(uid)
            Z.pop(uid, None)
            
            # 🟢 MEMORY LEAK FIX: Stop user client properly
            if uid in UC:
                try: 
                    await UC[uid].stop()
                except Exception as e: 
                    pass
                finally:
                    UC.pop(uid, None)
                    
            # 🟢 DELETE REFERENCE VIDEO: Batch khatam hone par kachra saaf karo
            ref_file = f"temp_reference_{uid}.mp4"
            if os.path.exists(ref_file):
                try:
                    os.remove(ref_file)
                    logger.info("🧹 Reference video deleted after batch completion.")
                except Exception as e:
                    logger.error(f"Failed to delete reference video: {e}")