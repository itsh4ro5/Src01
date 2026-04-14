import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from config import MONGO_DB, DB_NAME, OWNER_ID
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "super_secret_key_change_me" 

# Sync MongoDB for Flask Backend
try:
    client = MongoClient(MONGO_DB)
    db = client[DB_NAME]
    admin_auth = db["admin_auth"]
    admin_logs = db["admin_logs"]
    users_col = db["users"]
    premium_col = db["premium_users"]
except Exception as e:
    print(f"Database connection error: {e}")

# 🟢 NEW: Direct JSON Reader function to avoid Pyrogram asyncio threading errors
def get_active_task(user_id):
    try:
        if os.path.exists("active_users.json"):
            with open("active_users.json", "r") as f:
                data = json.load(f)
                return data.get(str(user_id))
    except Exception as e:
        print(f"Task read error: {e}")
    return None

@app.route("/", methods=["GET", "POST"])
def login():
    if "admin_id" in session:
        return redirect(url_for("dashboard"))
        
    if request.method == "POST":
        tg_id = request.form.get("tg_id")
        password = request.form.get("password")
        
        try:
            tg_id = int(tg_id)
            admin = admin_auth.find_one({"admin_id": tg_id, "password": password})
            
            if admin:
                session["admin_id"] = tg_id
                session["admin_name"] = admin.get("admin_name", "Admin")
                
                # RBAC Logic
                if tg_id in OWNER_ID:
                    session["role"] = "owner"
                else:
                    session["role"] = "admin"
                    
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid Telegram ID or Password!", "error")
        except ValueError:
            flash("Telegram ID must be a number.", "error")
            
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "admin_id" not in session:
        return redirect(url_for("login"))
        
    admin_id = session["admin_id"]
    is_owner = session.get("role") == "owner"

    total_users = users_col.count_documents({})
    premium_users_count = premium_col.count_documents({})

    if is_owner:
        # OWNER VIEW
        logs = list(admin_logs.find().sort("timestamp", -1).limit(50))
        premium_users_list = list(premium_col.find({}))
        view_type = "Global Overview (Owner)"
        return render_template("owner_dashboard.html", 
                               admin_name=session["admin_name"],
                               total_users=total_users, 
                               premium_users=premium_users_count,
                               users=premium_users_list,
                               logs=logs,
                               view_type=view_type,
                               is_owner=is_owner)
    else:
        # ADMIN VIEW
        current_task = get_active_task(admin_id) # 🟢 Using new safe function
            
        logs = list(admin_logs.find({"admin_id": admin_id}).sort("timestamp", -1).limit(50))
        view_type = f"Personal Dashboard ({session['admin_name']})"
        return render_template("user_dashboard.html", 
                               admin_name=session["admin_name"],
                               total_users=total_users, 
                               premium_users=premium_users_count,
                               task=current_task,
                               logs=logs,
                               view_type=view_type,
                               is_owner=is_owner)

@app.route("/admin/users")
def list_premium_users():
    if session.get("role") != "owner":
        return redirect(url_for("dashboard"))
    p_users = list(premium_col.find({}))
    return render_template("user_list.html", users=p_users)

@app.route("/admin/user/<int:user_id>")
def user_details(user_id):
    if session.get("role") != "owner" and session.get("admin_id") != user_id:
        return redirect(url_for("dashboard"))

    user_info = premium_col.find_one({"user_id": user_id})
    active_task = get_active_task(user_id) # 🟢 Using new safe function
        
    user_logs = list(admin_logs.find({"admin_id": user_id}).sort("timestamp", -1).limit(20))
    return render_template("user_profile.html", user=user_info, task=active_task, logs=user_logs)

# --- NAYA FEATURE: ADD USER VIA WEB ---
@app.route("/admin/add_user", methods=["POST"])
def web_add_user():
    if session.get("role") != "owner":
        return redirect(url_for("dashboard"))

    try:
        tg_id = int(request.form.get("tg_id"))
        val = int(request.form.get("duration_value"))
        unit = request.form.get("duration_unit")

        now = datetime.now()
        if unit == "min": exp = now + timedelta(minutes=val)
        elif unit == "hours": exp = now + timedelta(hours=val)
        elif unit == "days": exp = now + timedelta(days=val)
        elif unit == "weeks": exp = now + timedelta(weeks=val)
        elif unit == "month": exp = now + timedelta(days=30 * val)
        elif unit == "year": exp = now + timedelta(days=365 * val)
        else: exp = now + timedelta(days=val)

        # Database update
        premium_col.update_one(
            {"user_id": tg_id},
            {"$set": {"user_id": tg_id, "subscription_start": now, "subscription_end": exp, "expireAt": exp}},
            upsert=True
        )

        # Admin log me save karna
        admin_logs.insert_one({
            "admin_id": session["admin_id"],
            "admin_name": session.get("admin_name", "Boss"),
            "action": f"Web App: Added Premium ({val} {unit})",
            "target": str(tg_id),
            "timestamp": now
        })
        flash(f"User {tg_id} successfully added!", "success")
    except Exception as e:
        flash(f"Error adding user: {e}", "error")

    return redirect(url_for("list_premium_users"))

# --- NAYA FEATURE: REMOVE USER VIA WEB ---
@app.route("/admin/remove_user/<int:tg_id>")
def web_remove_user(tg_id):
    if session.get("role") != "owner":
        return redirect(url_for("dashboard"))

    # Premium se hatana aur web password delete karna
    premium_col.delete_one({"user_id": tg_id})
    admin_auth.delete_one({"admin_id": tg_id}) 

    # Admin log me save karna
    admin_logs.insert_one({
        "admin_id": session["admin_id"],
        "admin_name": session.get("admin_name", "Boss"),
        "action": "Web App: Revoked Premium",
        "target": str(tg_id),
        "timestamp": datetime.now()
    })
    flash(f"User {tg_id} has been removed and banned from web panel.", "error")
    return redirect(url_for("list_premium_users"))

# --- NAYA FEATURE: CLEAR HISTORY (LOGS) ---
@app.route("/clear_logs")
def clear_logs():
    if "admin_id" not in session:
        return redirect(url_for("login"))
        
    admin_id = session["admin_id"]
    is_owner = session.get("role") == "owner"
    
    try:
        if is_owner:
            # Boss clears ALL logs (Database space saved!)
            admin_logs.delete_many({})
            flash("All global logs have been cleared successfully! Space saved.", "success")
        else:
            # Premium User clears ONLY their own logs
            admin_logs.delete_many({"admin_id": admin_id})
            flash("Your history has been cleared successfully!", "success")
    except Exception as e:
        flash(f"Error clearing logs: {e}", "error")
        
    return redirect(url_for("dashboard"))    

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)