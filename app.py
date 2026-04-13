import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from config import MONGO_DB, DB_NAME, OWNER_ID

app = Flask(__name__)
# Session encryption ke liye ise ek strong random string se replace karna chahein toh kar sakte hain
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

@app.route("/", methods=["GET", "POST"])
def login():
    # Agar user already logged in hai, toh seedha dashboard par bhejo
    if "admin_id" in session:
        return redirect(url_for("dashboard"))
        
    if request.method == "POST":
        tg_id = request.form.get("tg_id")
        password = request.form.get("password")
        
        try:
            tg_id = int(tg_id)
            # Database me Telegram ID aur Password verify karna
            admin = admin_auth.find_one({"admin_id": tg_id, "password": password})
            
            if admin:
                # Login Success - Session set karein
                session["admin_id"] = tg_id
                session["admin_name"] = admin.get("admin_name", "Admin")
                
                # Role-Based Access Control (RBAC)
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
    # Agar user bina login kiye dashboard access kare, toh login page par bhejo
    if "admin_id" not in session:
        return redirect(url_for("login"))
        
    admin_id = session["admin_id"]
    is_owner = session.get("role") == "owner"

    # Database Stats Fetching (Total users bot ke liye common rahenge)
    total_users = users_col.count_documents({})
    premium_users = premium_col.count_documents({})

    if is_owner:
        # OWNER VIEW: Sab kuch dikhao (Last 50 global logs)
        logs = list(admin_logs.find().sort("timestamp", -1).limit(50))
        view_type = "Global Overview (Owner)"
    else:
        # ADMIN VIEW: Sirf khudka data (Last 50 personal logs)
        logs = list(admin_logs.find({"admin_id": admin_id}).sort("timestamp", -1).limit(50))
        view_type = f"Personal Logs (Admin: {session['admin_name']})"

    return render_template("dashboard.html", 
                           admin_name=session["admin_name"],
                           total_users=total_users, 
                           premium_users=premium_users,
                           logs=logs,
                           view_type=view_type,
                           is_owner=is_owner)

@app.route("/logout")
def logout():
    # Session ko clear karke wapas login page par bhejna
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)