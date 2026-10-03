import os, time, math, threading, requests
from flask import Flask
from dotenv import load_dotenv
load_dotenv()

from binance.client import Client

API_KEY = os.getenv("BINANCE_API") or os.getenv("BINANCE_API_KEY") or ""
API_SECRET = os.getenv("BINANCE_SECRET") or os.getenv("BINANCE_API_SECRET") or ""
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or ""
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or ""
PROXY_URL = os.getenv("PROXY_URL") or "http://pjaaqimr:alt6s2a3hin@31.59.20.176:6754"

app = Flask(__name__)
@app.route('/')
def home():
    return "Timothy Bot LIVE - 2025"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
threading.Thread(target=run_web, daemon=True).start()

print("=== BOOTING BOT ===")
print(f"API_KEY exists: {bool(API_KEY)}")
print(f"Proxy: {PROXY_URL[:30]}")

# Connect Binance
try:
    client = Client(API_KEY, API_SECRET, requests_params={"proxies":{"http":PROXY_URL,"https":PROXY_URL}, "timeout":20})
    client.API_URL = "https://api1.binance.com/api"
    client.ping()
    print("BINANCE CONNECTED VIA PROXY")
except Exception as e:
    print(f"Proxy fail {e}, trying direct api1")
    try:
        client = Client(API_KEY, API_SECRET)
        client.API_URL = "https://api1.binance.com/api"
        client.ping()
        print("BINANCE CONNECTED DIRECT")
    except Exception as e2:
        print(f"BINANCE FAILED: {e2}")
        client = None

# Keep alive loop
while True:
    print("Bot alive... waiting")
    time.sleep(60)
