# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  
# See LICENSE file in the repository root for full license text.

import os, re, time, asyncio, json, logging
import random
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import UserNotParticipant, FloodWait
from config import API_ID, API_HASH, LOG_GROUP, STRING, FORCE_SUB, FREEMIUM_LIMIT, PREMIUM_LIMIT
from utils.func import get_user_data, screenshot, thumbnail, get_video_metadata, IS_PAUSED, save_user_data
from utils.func import get_user_data_key, process_text_with_rules, is_premium_user, E
from shared_client import app as X
from plugins.settings import rename_file
from plugins.start import subscribe as sub
from utils.custom_filters import login_in_progress
from utils.encrypt import dcs
from typing import Dict, Any, Optional

# 🟢 Pillow Library import for custom thumbnail watermark
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("⚠️ Pillow not installed! Run 'pip install Pillow'")
    Image, ImageDraw, ImageFont = None, None, None

# 🟢 LOGGING SETUP
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger("pyrogram.session.session").setLevel(logging.ERROR)

Y = None if not STRING else __import__('shared_client').userbot
Z, P, UB, UC = {}, {}, {}, {}

ACTIVE_USERS = {}
ACTIVE_USERS_FILE = "active_users.json"

def sanitize(filename):
    return re.sub(r'[<>:"/\\|?*\']', '_', filename).strip(" .")[:255]

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
        with open(ACTIVE_USERS_FILE, 'w') as f:
            json.dump(ACTIVE_USERS, f)
    except Exception as e:
        pass

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

def get_batch_info(user_id: int) -> Optional[Dict[str, Any]]:
    return ACTIVE_USERS.get(str(user_id))

ACTIVE_USERS = load_active_users()

async def upd_dlg(c):
    try:
        async for _ in c.get_dialogs(limit=100): pass
        return True
    except Exception:
        return False

# 🟢 ROBUST FETCHING
async def get_msg(c, u, i, d, lt):
    logger.info(f"Fetch Request -> Chat: {i} | MsgID: {d} | Type: {lt}")
    try:
        if lt == 'public':
            try:
                msg = await c.get_messages(i, d)
                if msg and not getattr(msg, "empty", False):
                    logger.info("✅ Message fetched successfully by Bot")
                    return msg
            except FloodWait as fw:
                logger.warning(f"⚠️ FloodWait on Bot! Sleeping {fw.value}s...")
                await asyncio.sleep(fw.value + 2)
                msg = await c.get_messages(i, d)
                if msg and not getattr(msg, "empty", False):
                    return msg
            except Exception as e:
                logger.debug(f"Bot failed to fetch: {e}")
            
            if u:
                logger.info("Trying to fetch via Userbot...")
                try:
                    msg = await u.get_messages(i, d)
                    if msg and not getattr(msg, "empty", False):
                        logger.info("✅ Message fetched successfully by Userbot")
                        return msg
                except FloodWait as fw:
                    await asyncio.sleep(fw.value + 2)
                    msg = await u.get_messages(i, d)
                    if msg and not getattr(msg, "empty", False):
                        return msg
                except Exception:
                    pass
                
                try:
                    await u.join_chat(i)
                    msg = await u.get_messages(i, d)
                    if msg and not getattr(msg, "empty", False):
                        logger.info("✅ Message fetched after joining by Userbot")
                        return msg
                except Exception:
                    pass
            
            logger.warning(f"❌ Could not fetch Public Message {d} from {i}")
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
                            if result and not getattr(result, "empty", False):
                                logger.info(f"✅ Message Found in private chat {target_id}!")
                                return result
                        except FloodWait as fw:
                            logger.warning(f"⚠️ FloodWait Active! Sleeping {fw.value}s")
                            await asyncio.sleep(fw.value + 2)
                            result = await u.get_messages(target_id, d)
                            if result and not getattr(result, "empty", False):
                                return result
                        except Exception:
                            pass
                    
                    try:
                        async for _ in u.get_dialogs(limit=200): pass
                        for target_id in targets:
                            try:
                                result = await u.get_messages(target_id, d)
                                if result and not getattr(result, "empty", False):
                                    return result
                            except Exception:
                                pass
                    except Exception:
                        pass
                    return None
                except Exception as e:
                    logger.error(f'Private channel error: {e}')
                    return None
            return None
    except Exception as e:
        logger.error(f'Error in get_msg: {e}')
        return None

async def get_ubot(uid):
    bt = await get_user_data_key(uid, "bot_token", None)
    if not bt: return None
    if uid in UB: return UB.get(uid)
    try:
        bot = Client(f"user_{uid}", bot_token=bt, api_id=API_ID, api_hash=API_HASH)
        await bot.start()
        UB[uid] = bot
        return bot
    except Exception:
        return None

async def get_uclient(uid):
    ud = await get_user_data(uid)
    ubot = UB.get(uid)
    cl = UC.get(uid)
    
    if cl:
        if not cl.is_connected:
            try: await cl.connect()
            except: pass
        return cl
        
    if not ud: 
        return ubot if ubot else None
        
    xxx = ud.get('session_string')
    if xxx:
        try:
            ss = dcs(xxx)
            gg = Client(f'{uid}_client', api_id=API_ID, api_hash=API_HASH, device_model="v3saver", session_string=ss)
            await gg.start()
            UC[uid] = gg
            return gg
        except Exception as e:
            logger.error(f'User client error: {e}')
            return ubot if ubot else Y
    return Y

async def prog(c, t, C, h, m, st):
    global P
    p = c / t * 100
    interval = 10 if t >= 100 * 1024 * 1024 else 20 if t >= 50 * 1024 * 1024 else 30 if t >= 10 * 1024 * 1024 else 50
    step = int(p // interval) * interval
    if m not in P or P[m] != step or p >= 100:
        P[m] = step
        c_mb = c / (1024 * 1024)
        t_mb = t / (1024 * 1024)
        bar = '🟢' * int(p / 10) + '🔴' * (10 - int(p / 10))
        speed = c / (time.time() - st) / (1024 * 1024) if time.time() > st else 0
        eta = time.strftime('%M:%S', time.gmtime((t - c) / (speed * 1024 * 1024))) if speed > 0 else '00:00'
        try:
            await C.edit_message_text(h, m, f"__**Pyro Handler...**__\n\n{bar}\n\n⚡**__Completed__**: {c_mb:.2f} MB / {t_mb:.2f} MB\n📊 **__Done__**: {p:.2f}%\n🚀 **__Speed__**: {speed:.2f} MB/s\n⏳ **__ETA__**: {eta}\n\n**__Powered by Team SPY__**")
        except: pass
        if p >= 100: P.pop(m, None)

# 🟢 CAPTION BEAUTIFIER & CUSTOM THUMBNAIL LOGIC
def beautify_caption(text):
    if not text: return ""
    replacements = {
        r"(?i)Index\s*:": "\nIndex:",
        r"(?i)Title\s*:": "\n\nTitle:",
        r"(?i)Topic\s*:": "\n\nTopic:",
        r"(?i)Batch\s*:": "\n\nBatch:",
        r"(?i)Extracted By\s*:": "\n\nExtracted By:",
        r"(?i)Quality\s*:": "\n\nQuality:",
        r"(?i)Size\s*:": "\n\nSize:"
    }
    for pattern, new_text in replacements.items(): 
        text = re.sub(pattern, new_text, text)
    text = re.sub(r'\n\s*\n', '\n\n', text).strip()
    return text

async def add_thumbnail_watermark(video_path, uid):
    if not video_path or not Image: return None
    try:
        thumb_path = f"{video_path}_thumb.jpg"
        cmd = ["ffmpeg", "-i", video_path, "-ss", "00:00:01", "-vframes", "1", "-y", thumb_path, "-loglevel", "quiet"]
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()
        
        if os.path.exists(thumb_path):
            img = Image.open(thumb_path)
            draw = ImageDraw.Draw(img)
            
            # Using default bold font logic for custom watermark text
            try:
                # Assuming standard TTF location or default
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(img.width/15))
            except:
                font = ImageFont.load_default()
            
            wm_text = "IT'S H4R"
            
            # Box setup behind text for readability
            text_bbox = draw.textbbox((0, 0), wm_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            x = (img.width - text_width) / 2
            y = (img.height - text_height) / 2
            
            box_padding = int(img.width/50)
            draw.rectangle([x - box_padding, y - box_padding, x + text_width + box_padding, y + text_height + box_padding], fill=(0, 0, 0, 150))
            
            draw.text((x, y), wm_text, font=font, fill="white")
            img.save(thumb_path)
            return thumb_path
    except Exception as e:
        logger.error(f"Thumbnail Watermark Error: {e}")
    return None

async def send_direct(c, m, tcid, ft=None, rtmid=None):
    try:
        if m.video:
            await c.send_video(tcid, m.video.file_id, caption=ft, duration=m.video.duration, width=m.video.width, height=m.video.height, reply_to_message_id=rtmid)
        elif m.video_note:
            await c.send_video_note(tcid, m.video_note.file_id, reply_to_message_id=rtmid)
        elif m.voice:
            await c.send_voice(tcid, m.voice.file_id, reply_to_message_id=rtmid)
        elif m.sticker:
            await c.send_sticker(tcid, m.sticker.file_id, reply_to_message_id=rtmid)
        elif m.audio:
            await c.send_audio(tcid, m.audio.file_id, caption=ft, duration=m.audio.duration, performer=m.audio.performer, title=m.audio.title, reply_to_message_id=rtmid)
        elif m.photo:
            photo_id = m.photo.file_id if hasattr(m.photo, 'file_id') else m.photo[-1].file_id
            await c.send_photo(tcid, photo_id, caption=ft, reply_to_message_id=rtmid)
        elif m.document:
            await c.send_document(tcid, m.document.file_id, caption=ft, file_name=m.document.file_name, reply_to_message_id=rtmid)
        else:
            return False
        return True
    except Exception as e:
        logger.error(f'Direct send error: {e}')
        return False

async def process_msg(c, u, m, d, lt, uid, i):
    # 🟢 PEER_ID_INVALID FIX: Ensure d (Chat ID) is always an Integer!
    if isinstance(d, str):
        try: d = int(d)
        except Exception: pass

    logger.info(f"Processing Message ID: {m.id} | UID: {uid} | TargetUser: {d}")
    try:
        cfg_chat = await get_user_data_key(d, 'chat_id', None)
        tcid = d
        rtmid = None
        if cfg_chat:
            if '/' in cfg_chat:
                parts = cfg_chat.split('/', 1)
                tcid = int(parts[0])
                rtmid = int(parts[1]) if len(parts) > 1 else None
            else:
                tcid = int(cfg_chat)
        
        # 🟢 PEER CACHE: Ensure Bot knows Target Chat before attempting upload
        try: await c.get_chat(tcid)
        except Exception: pass
        
        if m.media:
            orig_text = m.caption.markdown if m.caption else ''
            proc_text = await process_text_with_rules(d, orig_text)
            user_cap = await get_user_data_key(d, 'caption', '')
            raw_caption = f'{proc_text}\n\n{user_cap}' if proc_text and user_cap else user_cap if user_cap else proc_text
            
            # Apply new caption beautifier
            ft = beautify_caption(raw_caption)
            
            is_restricted = getattr(m.chat, "has_protected_content", False)
            
            if lt == 'public' and not is_restricted:
                logger.info("Public File (Unrestricted): Sending Directly...")
                success = await send_direct(c, m, tcid, ft, rtmid)
                if success:
                    return 'Sent directly.'
                logger.warning("Direct send failed! Falling back to advanced extraction...")
            elif lt == 'public' and is_restricted:
                logger.info("Public File is RESTRICTED (SRC ON). Routing to Download/Forward method...")
            
            p = await c.send_message(d, '⏳ Initializing...')
            
            # 🟢 RESTORED FAST FORWARD LOGIC
            forward_mode = await get_user_data_key(uid, "forward_mode", False)
            if forward_mode and not is_restricted:
                logger.info("Fast Forward is ON. Attempting direct copy...")
                try:
                    client_to_use = getattr(m, '_client', u if u else c)
                    await client_to_use.copy_message(
                        chat_id=tcid,
                        from_chat_id=m.chat.id,
                        message_id=m.id,
                        caption=ft if ft else None,
                        reply_to_message_id=rtmid
                    )
                    await c.delete_messages(d, p.id)
                    return 'Fast Forwarded ✅'
                except Exception as e:
                    logger.error(f"Fast forward failed: {e}")
                    await c.edit_message_text(d, p.id, f"⚠️ **Forward Error:** `{str(e)[:30]}`\n🔄 Downloading...")
                    await asyncio.sleep(2)
            elif forward_mode and is_restricted:
                logger.info("Fast Forward bypassed because channel is Restricted. Downloading...")
            
            st = time.time()
            logger.info("Starting Media Download...")
            await c.edit_message_text(d, p.id, '⬇️ Downloading...')

            c_name = f"{time.time()}"
            original_ext = ""
            
            if m.video:
                file_name = m.video.file_name
                original_ext = ".mp4"
                if not file_name: file_name = f"{time.time()}.mp4"
                c_name = sanitize(file_name)
            elif m.audio:
                file_name = m.audio.file_name
                original_ext = ".mp3"
                if not file_name: file_name = f"{time.time()}.mp3"
                c_name = sanitize(file_name)
            elif m.document:
                file_name = m.document.file_name
                if file_name: original_ext = os.path.splitext(file_name)[1].lower()
                else:
                    original_ext = ".pdf" 
                    file_name = f"{time.time()}{original_ext}"
                c_name = sanitize(file_name)
            elif m.photo:
                file_name = f"{time.time()}.jpg"
                original_ext = ".jpg"
                c_name = sanitize(file_name)
    
            try:
                client_to_use = getattr(m, '_client', u if u else c)
                logger.info(f"Downloading with Client: {client_to_use.name if hasattr(client_to_use, 'name') else 'User Session'}")
                f = await client_to_use.download_media(m, file_name=c_name, progress=prog, progress_args=(c, d, p.id, st))
            except Exception as dl_err:
                logger.error(f"Download Exception: {dl_err}")
                f = None
                
            if not f:
                logger.error("Download Failed. File is None.")
                await c.edit_message_text(d, p.id, 'Failed.')
                return 'Failed.'
            
            logger.info(f"File downloaded successfully to: {f}")
            await c.edit_message_text(d, p.id, 'Renaming...')
            
            if (m.video and m.video.file_name) or (m.audio and m.audio.file_name) or (m.document and m.document.file_name):
                renamed_f = await rename_file(f, d, p)
                if original_ext and not renamed_f.lower().endswith(original_ext):
                    corrected_name = renamed_f + original_ext
                    os.rename(renamed_f, corrected_name)
                    f = corrected_name
                else:
                    f = renamed_f
            
            fsize = os.path.getsize(f) / (1024 * 1024 * 1024)
            th = None
            
            if m.video or str(f).endswith(('.mp4', '.mkv')):
                 th = await add_thumbnail_watermark(f, uid)
            if not th:
                 th = thumbnail(d)
            
            if fsize > 2 and Y:
                logger.warning("File > 2GB detected. Routing through alternative Y Client (LOG_GROUP).")
                st = time.time()
                await c.edit_message_text(d, p.id, 'File is larger than 2GB. Using alternative method...')
                await upd_dlg(Y)
                mtd = await get_video_metadata(f)
                dur, h, w = mtd['duration'], mtd['width'], mtd['height']
                
                send_funcs = {'video': Y.send_video, 'video_note': Y.send_video_note, 
                            'voice': Y.send_voice, 'audio': Y.send_audio, 
                            'photo': Y.send_photo, 'document': Y.send_document}
                
                for mtype, func in send_funcs.items():
                    if f.endswith('.mp4'): mtype = 'video'
                    if getattr(m, mtype, None):
                        sent = await func(LOG_GROUP, f, thumb=th if mtype == 'video' else None, 
                                        duration=dur if mtype == 'video' else None,
                                        height=h if mtype == 'video' else None,
                                        width=w if mtype == 'video' else None,
                                        caption=ft if m.caption and mtype not in ['video_note', 'voice'] else None, 
                                        reply_to_message_id=rtmid, progress=prog, progress_args=(c, d, p.id, st))
                        break
                else:
                    sent = await Y.send_document(LOG_GROUP, f, thumb=th, caption=ft if m.caption else None,
                                                reply_to_message_id=rtmid, progress=prog, progress_args=(c, d, p.id, st))
                
                await c.copy_message(d, LOG_GROUP, sent.id)
                os.remove(f)
                await c.delete_messages(d, p.id)
                
                return 'Done (Large file).'
            
            logger.info("Starting Media Upload...")
            await c.edit_message_text(d, p.id, 'Uploading...')
            st = time.time()

            try:
                video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ogv']
                audio_extensions = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus', '.aiff', '.ac3']
                file_ext = os.path.splitext(f)[1].lower()
                
                if file_ext in ['.pdf', '.zip', '.rar', '.txt', '.doc', '.docx', '.apk', '.epub', '.py']:
                    await c.send_document(tcid, document=f, caption=ft if m.caption else None, 
                                        progress=prog, progress_args=(c, d, p.id, st), 
                                        reply_to_message_id=rtmid)
                elif m.video or file_ext in video_extensions:
                    mtd = await get_video_metadata(f)
                    dur, h, w = mtd['duration'], mtd['width'], mtd['height']
                    await c.send_video(tcid, video=f, caption=ft if m.caption else None, 
                                    thumb=th, width=w, height=h, duration=dur, 
                                    progress=prog, progress_args=(c, d, p.id, st), 
                                    reply_to_message_id=rtmid)
                elif m.video_note:
                    await c.send_video_note(tcid, video_note=f, progress=prog, 
                                        progress_args=(c, d, p.id, st), reply_to_message_id=rtmid)
                elif m.voice:
                    await c.send_voice(tcid, f, progress=prog, progress_args=(c, d, p.id, st), 
                                    reply_to_message_id=rtmid)
                elif m.sticker:
                    await c.send_sticker(tcid, m.sticker.file_id, reply_to_message_id=rtmid)
                elif m.audio or file_ext in audio_extensions:
                    await c.send_audio(tcid, audio=f, caption=ft if m.caption else None, 
                                    thumb=th, progress=prog, progress_args=(c, d, p.id, st), 
                                    reply_to_message_id=rtmid)
                elif m.photo:
                    await c.send_photo(tcid, photo=f, caption=ft if m.caption else None, 
                                    progress=prog, progress_args=(c, d, p.id, st), 
                                    reply_to_message_id=rtmid)
                else:
                    await c.send_document(tcid, document=f, caption=ft if m.caption else None, 
                                        progress=prog, progress_args=(c, d, p.id, st), 
                                        reply_to_message_id=rtmid)
            except Exception as e:
                logger.error(f"Upload Exception: {e}")
                await c.edit_message_text(d, p.id, f'Upload failed: {str(e)[:30]}')
                if os.path.exists(f): os.remove(f)
                return 'Failed.'
            
            logger.info("Upload Completed Successfully! Removing temp file.")
            os.remove(f)
            await c.delete_messages(d, p.id)
            
            return 'Done.'
            
        elif m.text:
            logger.info("Processing Text Message...")
            orig_text = m.text.markdown
            proc_text = await process_text_with_rules(d, orig_text)
            user_cap = await get_user_data_key(d, 'caption', '')
            raw_caption = f'{proc_text}\n\n{user_cap}' if proc_text and user_cap else user_cap if user_cap else proc_text
            
            ft = beautify_caption(raw_caption)
            await c.send_message(tcid, text=ft if ft else orig_text, reply_to_message_id=rtmid)
            return 'Sent.'
        else:
            return 'Skipped: Unsupported Type.'
            
    except Exception as e:
        logger.error(f"Global Error in process_msg: {e}")
        return f'Error: {str(e)[:50]}'

@X.on_message(filters.command(['batch', 'single']))
async def process_cmd(c, m):
    uid = m.from_user.id
    cmd = m.command[0]
    logger.info(f"Command /{cmd} initiated by {uid}")
    
    if FREEMIUM_LIMIT == 0 and not await is_premium_user(uid):
        await m.reply_text("This bot does not provide free servies, get subscription from OWNER")
        return
    
    if await sub(c, m) == 1: return
    pro = await m.reply_text('Doing some checks hold on...')
    
    if is_user_active(uid):
        logger.warning(f"User {uid} already has an active task.")
        await pro.edit('You have an active task. Use /stop to cancel it.')
        return
    
    ubot = await get_ubot(uid)
    if not ubot:
        logger.warning(f"User {uid} has no bot_token set.")
        await pro.edit('Add your bot with /setbot first')
        return
    
    Z[uid] = {'step': 'start' if cmd == 'batch' else 'start_single'}
    await pro.edit(f'Send {"start link..." if cmd == "batch" else "link you to process"}.')

@X.on_message(filters.command(['cancel', 'stop']))
async def cancel_cmd(c, m):
    uid = m.from_user.id
    logger.info(f"Cancel request by {uid}")
    if is_user_active(uid):
        if await request_batch_cancel(uid):
            await m.reply_text('Cancellation requested. The current batch will stop after the current download completes.')
        else:
            await m.reply_text('Failed to request cancellation. Please try again.')
    else:
        await m.reply_text('No active batch process found.')

# 🟢 ADDED ID COMMAND 
@X.on_message(filters.command("id"))
async def get_id_cmd(client, message):
    text = f"🆔 **Current Chat ID:** `{message.chat.id}`\n"
    if message.reply_to_message:
        if message.reply_to_message.forward_from_chat: 
            text += f"📢 **Forwarded Chat ID:** `{message.reply_to_message.forward_from_chat.id}`\n"
        elif message.reply_to_message.forward_from: 
            text += f"👤 **Forwarded User ID:** `{message.reply_to_message.forward_from.id}`\n"
    await message.reply(text)

@X.on_message(filters.command("forward"))
async def toggle_forward(c, m):
    uid = m.from_user.id
    current_status = await get_user_data_key(uid, "forward_mode", False)
    new_status = not current_status
    await save_user_data(uid, "forward_mode", new_status)
    
    if new_status:
        await m.reply_text("✅ **Fast Forward Mode ON**\n\nAb jin channels me forward ON (unrestricted) hoga, wahan bot bina download/upload kiye files ko seedha clone karega. \n\n⚡ **Fayda:** 100x Fast speed aur aapka set kiya hua custom caption apply hoga!")
    else:
        await m.reply_text("❌ **Fast Forward Mode OFF**\n\nAb bot sabhi files ko hamesha pehle download karega aur phir upload karega.")

@X.on_message(filters.text & filters.private & ~login_in_progress & ~filters.command([
    'start', 'batch', 'cancel', 'login', 'logout', 'stop', 'set', 
    'pay', 'redeem', 'gencode', 'single', 'generate', 'keyinfo', 'encrypt', 'decrypt', 'keys', 'setbot', 'rembot', 'forward', 'id']))
async def text_handler(c, m):
    uid = m.from_user.id
    
    if uid not in Z:
        if m.text and ("t.me/" in m.text or "telegram.me/" in m.text):
            logger.info(f"Auto-detected link from {uid}")
            i, d, lt = E(m.text)
            if not i or not d:
                await m.reply_text('❌ Invalid link format.')
                return
            Z[uid] = {'step': 'count', 'cid': i, 'sid': d, 'lt': lt}
            await m.reply_text('🔗 **Link Detected!**\n\n🔢 **Kitne messages nikalne hain?**\n👉 (Sirf 1 nikalna है तो `1` लिखें, या Batch के लिए total number भेजें)')
            return
        else:
            return
            
    s = Z[uid].get('step')
    logger.info(f"Text Handler Step: {s} | User: {uid}")
    
    x = await get_ubot(uid)
    if not x:
        await m.reply("Add your bot /setbot `token`")
        return

    if s == 'start':
        L = m.text
        i, d, lt = E(L)
        if not i or not d:
            logger.warning(f"Invalid link from user {uid}: {L}")
            await m.reply_text('Invalid link format.')
            Z.pop(uid, None)
            return
        Z[uid].update({'step': 'count', 'cid': i, 'sid': d, 'lt': lt})
        await m.reply_text('How many messages?')

    elif s == 'start_single':
        L = m.text
        i, d, lt = E(L)
        if not i or not d:
            logger.warning(f"Invalid link from user {uid}: {L}")
            await m.reply_text('Invalid link format.')
            Z.pop(uid, None)
            return

        Z[uid].update({'step': 'process_single', 'cid': i, 'sid': d, 'lt': lt})
        i, s, lt = Z[uid]['cid'], Z[uid]['sid'], Z[uid]['lt']
        pt = await m.reply_text('Processing...')
        
        ubot = UB.get(uid)
        if not ubot:
            await pt.edit('Add bot with /setbot first')
            Z.pop(uid, None)
            return
        
        uc = await get_uclient(uid)
        if not uc:
            logger.error(f"User Client not active for {uid}")
            await pt.edit('Cannot proceed without user client.')
            Z.pop(uid, None)
            return
            
        if is_user_active(uid):
            await pt.edit('Active task exists. Use /stop first.')
            Z.pop(uid, None)
            return

        try:
            # 🟢 STRING TO INT BUG FIX
            target_chat_id = m.chat.id
            msg = await get_msg(ubot, uc, i, s, lt)
            if msg:
                logger.info(f"Initiating process for single msg {s}")
                res = await process_msg(ubot, uc, msg, target_chat_id, lt, uid, i)
                await pt.edit(f'1/1: {res}')
            else:
                logger.warning(f"Message {s} not found or skipped.")
                await pt.edit('⚠️ Message not found! (Private Channel / Removed)')
        except Exception as e:
            logger.error(f"Single Extraction Error: {e}")
            await pt.edit(f'Error: {str(e)[:50]}')
        finally:
            Z.pop(uid, None)

    elif s == 'count':
        if not m.text.isdigit():
            await m.reply_text('Enter valid number.')
            return
        
        count = int(m.text)
        maxlimit = PREMIUM_LIMIT if await is_premium_user(uid) else FREEMIUM_LIMIT

        if count > maxlimit:
            await m.reply_text(f'Maximum limit is {maxlimit}.')
            return

        logger.info(f"Starting batch for {count} messages for {uid}")
        Z[uid].update({'step': 'process', 'did': str(m.chat.id), 'num': count})
        i, s, n, lt = Z[uid]['cid'], Z[uid]['sid'], Z[uid]['num'], Z[uid]['lt']
        success = 0

        pt = await m.reply_text('Processing batch...')
        uc = await get_uclient(uid)
        ubot = UB.get(uid)
        
        if not uc or not ubot:
            await pt.edit('Missing client setup')
            Z.pop(uid, None)
            return
            
        if is_user_active(uid):
            await pt.edit('Active task exists')
            Z.pop(uid, None)
            return
        
        await add_active_batch(uid, {
            "total": n,
            "current": 0,
            "success": 0,
            "cancel_requested": False,
            "progress_message_id": pt.id
            })
        
        try:
            for j in range(n):
                
                while IS_PAUSED:
                    try: await pt.edit('Taking a human-like break... Paused for ~20 mins.')
                    except: pass
                    logger.info("Bot is in human-like break mode...")
                    await asyncio.sleep(random.uniform(55.5, 65.5))
                
                if should_cancel(uid):
                    logger.info(f"Batch cancelled by {uid}")
                    await pt.edit(f'Cancelled at {j}/{n}. Success: {success}')
                    break
                
                await update_batch_progress(uid, j, success)
                
                mid = int(s) + j
                logger.info(f"Fetching message {j+1}/{n} (ID: {mid})")
                
                try:
                    # 🟢 STRING TO INT BUG FIX
                    target_chat_id = m.chat.id
                    msg = await get_msg(ubot, uc, i, mid, lt)
                    if msg:
                        res = await process_msg(ubot, uc, msg, target_chat_id, lt, uid, i)
                        if res and any(x in res for x in ['Done', 'Copied', 'Sent', 'Forwarded']):
                            success += 1
                            logger.info(f"Message {mid} successfully processed.")
                    else:
                        logger.warning(f"⚠️ Skipped {mid}: Could not fetch message.")
                        try: await pt.edit(f"⚠️ Skipped {mid}: Not found.")
                        except: pass
                except Exception as e:
                    logger.error(f"Error on message {mid}: {e}")
                    try: await pt.edit(f'{j+1}/{n}: Error - {str(e)[:30]}')
                    except: pass
                
                if n > 1:
                    delay_time = random.uniform(17.5, 35.8)
                    try: await pt.edit(f'Sleeping for {delay_time:.2f}s to act like human & prevent ban...')
                    except: pass
                    logger.info(f"Sleeping for {delay_time:.2f} seconds...")
                    await asyncio.sleep(delay_time)
            
            if j+1 == n:
                logger.info(f"Batch completed for {uid}. Success: {success}/{n}")
                await m.reply_text(f'Batch Completed ✅ Success: {success}/{n}')
        
        finally:
            await remove_active_batch(uid)
            Z.pop(uid, None)
