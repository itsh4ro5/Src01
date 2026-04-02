import os
from dotenv import load_dotenv

load_dotenv()

# --- Utility function to get integer environment variables ---
def get_int_env(name, default=None):
    value = os.getenv(name)
    if value and value.lstrip('-').isdigit():
        return int(value)
    return default

# --- Utility function to get list of integer environment variables ---
def get_list_int_env(name, default=None):
    value = os.getenv(name)
    if value:
        return list(map(int, value.split()))
    return default or []

# VPS --- FILL COOKIES 🍪 in """ ... """ 

INST_COOKIES = """
# write up here insta cookies
"""

YTUB_COOKIES = """
# write here yt cookies
"""

# WARNING: Apni sensitive details yahan hardcode mat karo. Hugging Face ki Settings > Secrets me add karo.
API_ID = os.getenv("API_ID", "") 
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MONGO_DB = os.getenv("MONGO_DB", "")
OWNER_ID = list(map(int, os.getenv("OWNER_ID", "").split())) # list seperated via space
DB_NAME = os.getenv("DB_NAME", "")
STRING = os.getenv("STRING", None) # optional
LOG_GROUP = int(os.getenv("LOG_GROUP", "-1003604603493")) # optional with -100
FORCE_SUB = int(os.getenv("FORCE_SUB", "-1002556423278")) # optional with -100
MASTER_KEY = os.getenv("MASTER_KEY", "gK8HzLfT9QpViJcYeB5wRa3DmN7P2xUq") # for session encryption
IV_KEY = os.getenv("IV_KEY", "s7Yx5CpVmE3F") # for decryption
YT_COOKIES = os.getenv("YT_COOKIES", YTUB_COOKIES)
INSTA_COOKIES = os.getenv("INSTA_COOKIES", INST_COOKIES)
FREEMIUM_LIMIT = int(os.getenv("FREEMIUM_LIMIT", "500"))
PREMIUM_LIMIT = int(os.getenv("PREMIUM_LIMIT", "500"))
JOIN_LINK = os.getenv("JOIN_LINK", "https://t.me/+MdyINnB7oNxjYWJl") # this link for start command message
ADMIN_CONTACT = os.getenv("ADMIN_CONTACT", "https://t.me/H4R_Contact_bot")