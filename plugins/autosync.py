import asyncio
from pyrogram import Client, filters
from shared_client import app as X
from utils.func import db, is_premium_user

# AutoSync ka naya database collection
sync_col = db["autosync"]

@X.on_message(filters.command("autosync"))
async def setup_autosync(c, m):
    uid = m.from_user.id
    
    # 🟢 Premium Check
    if not await is_premium_user(uid):
        return await m.reply_text("❌ **VIP Feature!**\nAuto-Cloner use karne ke liye Premium purchase karein. (Set & Forget Mode)")
    
    if len(m.command) != 3:
        return await m.reply_text(
            "⚠️ **Format:** `/autosync [Source_ID] [Target_ID]`\n\n"
            "Ex: `/autosync -10012345678 -10098765432`\n"
            "Isse Source me aane wali nayi files automatically Target me upload ho jayengi!"
        )
        
    source_id = m.command[1]
    target_id = m.command[2]
    
    # Database me sync link save karna
    await sync_col.update_one(
        {"user_id": uid, "source_id": source_id},
        {"$set": {"target_id": target_id, "active": True}},
        upsert=True
    )
    
    await m.reply_text(f"✅ **Live Auto-Sync Activated! 🚀**\n\n**Source:** `{source_id}`\n**Target:** `{target_id}`\n\nAb jab bhi Source me koi nayi post aayegi, bot automatically use clone kar dega bina bot open kiye!")

@X.on_message(filters.command("delsync"))
async def stop_autosync(c, m):
    uid = m.from_user.id
    await sync_col.delete_many({"user_id": uid})
    await m.reply_text("🛑 Aapke saare active Auto-Sync tasks rok diye gaye hain.")

# --- 🟢 GLOBAL LISTENER FOR NEW POSTS ---
# Ye background me dekhta rahega ki kya kisi source me naya message aaya hai
@X.on_message(filters.channel, group=5)
async def live_cloner_listener(c, m):
    chat_id = str(m.chat.id)
    
    # Check karega ki jis channel me message aaya hai, kya wo kisi VIP ka 'source_id' hai?
    active_syncs = sync_col.find({"source_id": chat_id, "active": True})
    
    async for sync_data in active_syncs:
        uid = sync_data["user_id"]
        target_id = int(sync_data["target_id"])
        
        # Ek baar cross-verify karega ki user abhi bhi premium hai ya nahi
        if await is_premium_user(uid):
            try:
                # File ko target channel me Fast-Forward/Copy kar dega
                await m.copy(chat_id=target_id)
                # (Future Upgrade: Yahan par aap batch.py wala process_msg bhi call karwa sakte hain metadata hatane ke liye)
            except Exception as e:
                pass # Agar channel restrict hai ya admin rights nahi hain
        else:
            # Agar plan expire ho gaya hai, toh sync pause kar do
            await sync_col.update_one({"_id": sync_data["_id"]}, {"$set": {"active": False}})