import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from config import MONGO_DB, DB_NAME, OWNER_ID

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

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)