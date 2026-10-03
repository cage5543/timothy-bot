import os, time, math, threading, requests
from flask import Flask
from dotenv import load_dotenv
load_dotenv()
from binance.client import Client

API_KEY = os.getenv("BINANCE_API") or os.getenv("BINANCE_API_KEY") or ""
API_SECRET = os.getenv("BINANCE_SECRET") or os.getenv("BINANCE_API_SECRET") or ""
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or ""
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or ""
PROXY_URL = os.getenv("PROXY_URL") or "http://pjaaqimr:alt6s2a3hin@31.59.20.176:6754"

SYMBOLS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT","DOTUSDT","MATICUSDT","LINKUSDT","LTCUSDT","TRXUSDT","ETCUSDT","FILUSDT","UNIUSDT","ATOMUSDT","NEARUSDT","APTUSDT","ARBUSDT"]

app = Flask(__name__)
@app.route('/')
def home(): return "Timothy Bot LIVE - Trading"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

threading.Thread(target=run_web, daemon=True).start()

def tg(m):
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": m}, timeout=10)
    except: pass

def get_rsi(closes, p=14):
    if len(closes)<p+1: return 50
    deltas=[closes[i]-closes[i-1] for i in range(1,len(closes))]
    gains=[max(0,d) for d in deltas[-p:]]
    losses=[max(0,-d) for d in deltas[-p:]]
    avg_g=sum(gains)/p; avg_l=sum(losses)/p
    if avg_l==0: return 80
    rs=avg_g/avg_l
    return 100-(100/(1+rs))

print("=== BOOTING BOT ===")
print(f"API_KEY exists: {bool(API_KEY)}")
print(f"Proxy: {PROXY_URL}")

# CONNECT BINANCE WITH PROXY
client=None
try:
    print("Trying BINANCE via PROXY + api1...")
    client = Client(API_KEY, API_SECRET, requests_params={"proxies":{"http":PROXY_URL,"https":PROXY_URL},"timeout":30})
    client.API_URL = "https://api1.binance.com/api"
    client.ping()
    print("BINANCE CONNECTED VIA PROXY + api1!")
    tg("Bot Live - Binance via Proxy OK")
except Exception as e:
    print(f"Proxy fail: {e}")
    try:
        print("Trying direct api1...")
        client = Client(API_KEY, API_SECRET)
        client.API_URL = "https://api1.binance.com/api"
        client.ping()
        print("BINANCE CONNECTED DIRECT api1")
    except Exception as e2:
        print(f"BINANCE FAILED: {e2}")

if client:
    client.RECV_WINDOW=60000
    holding=None; buy_price=0
    print("Starting trading loop...")
    while True:
        try:
            usdt=float(client.get_asset_balance(asset='USDT')['free'])
            print(f"USDT {usdt:.2f} | Holding {holding}")
            # Your RSI logic here - simplified for now
            time.sleep(20)
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(10)
else:
    while True:
        print("No Binance client - waiting")
        time.sleep(60)
