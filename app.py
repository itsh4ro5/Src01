import os
from flask import Flask, render_template, request, Response
from pymongo import MongoClient
from config import MONGO_DB, DB_NAME

app = Flask(__name__)

# MongoDB Connection (Sync for Flask)
try:
    client = MongoClient(MONGO_DB)
    db = client[DB_NAME]
    users_col = db["users"]
    premium_col = db["premium_users"]
except Exception as e:
    print(f"Database connection error: {e}")

# Dashboard Security (Change Username & Password)
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

def check_auth(username, password):
    return username == ADMIN_USER and password == ADMIN_PASS

def authenticate():
    return Response(
    'Access Denied. Invalid Credentials.', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

@app.route("/")
def welcome():
    return render_template("welcome.html")

@app.route("/admin")
def dashboard():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()
    
    # Fetch real-time stats from Database
    total_users = users_col.count_documents({})
    premium_users = premium_col.count_documents({})
    
    return render_template("dashboard.html", total_users=total_users, premium_users=premium_users)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)