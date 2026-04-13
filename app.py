import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from config import MONGO_DB, DB_NAME

app = Flask(__name__)
app.secret_key = "super_secret_key_change_me" # Session encryption ke liye

# Sync MongoDB for Flask
client = MongoClient(MONGO_DB)
db = client[DB_NAME]
admin_auth = db["admin_auth"]
admin_logs = db["admin_logs"]
users_col = db["users"]
premium_col = db["premium_users"]

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
        
    total_users = users_col.count_documents({})
    premium_users = premium_col.count_documents({})
    
    # Get last 20 activities, sorted by newest first
    recent_logs = list(admin_logs.find().sort("timestamp", -1).limit(20))
    
    return render_template("dashboard.html", 
                           admin_name=session["admin_name"],
                           total_users=total_users, 
                           premium_users=premium_users,
                           logs=recent_logs)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)