import os, time, threading, requests
from flask import Flask
from dotenv import load_dotenv
load_dotenv()
from binance.client import Client

API_KEY = os.getenv("BINANCE_API","")
API_SECRET = os.getenv("BINANCE_SECRET","")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN","")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","")
PROXY_URL = os.getenv("PROXY_URL","")

app = Flask(__name__)
@app.route('/')
def home(): return "Bot Live - Waiting for Binance unban"
def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
threading.Thread(target=run_web, daemon=True).start()

def make_client():
    # Try proxy first, no auto ping
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    for base in ["https://data-api.binance.vision/api", "https://api1.binance.com/api", "https://api2.binance.com/api"]:
        try:
            print(f"Trying {base} with ping=False proxy={bool(proxies)}")
            c = Client(API_KEY, API_SECRET, requests_params={"proxies": proxies, "timeout":30} if proxies else {"timeout":30}, ping=False)
            c.API_URL = base
            c.ping() # manual ping once
            print(f"CONNECTED via {base}")
            return c
        except Exception as e:
            print(f"{base} failed: {e}")
            time.sleep(2)
    return None

print("=== BOOTING WITH ANTI-BAN ===")
client = make_client()
if not client:
    print("All APIs banned - sleeping 10min to unban")
    # Don't crash Render, just wait for unban
    while True:
        time.sleep(600)
        client = make_client()
        if client: break

# Trading loop here
while True:
    try:
        bal = client.get_asset_balance(asset='USDT')
        print(f"USDT {bal}")
        time.sleep(60)
    except Exception as e:
        print(f"Error {e} - waiting 60s")
        time.sleep(60)
