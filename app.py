12323import os
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def welcome():
    return render_template("welcome.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860)) # Changed to 7860 for Hugging Face
    app.run(host="0.0.0.0", port=port)