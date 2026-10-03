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
def home(): return "Timothy Bot LIVE - Trading Active"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
threading.Thread(target=run_web, daemon=True).start()

def tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": m}, timeout=10)
    except: pass

def get_rsi(closes, p=14):
    if len(closes) < p+1: return 50
    deltas = [closes[i]-closes[i-1] for i in range(1,len(closes))]
    gains = [max(0,d) for d in deltas[-p:]]
    losses = [max(0,-d) for d in deltas[-p:]]
    avg_g = sum(gains)/p; avg_l = sum(losses)/p
    if avg_l == 0: return 80
    return 100-(100/(1+avg_g/avg_l))

print("=== BOOTING BOT ===")
client = None
try:
    print("Trying via PROXY + api1...")
    client = Client(API_KEY, API_SECRET, requests_params={"proxies":{"http":PROXY_URL,"https":PROXY_URL},"timeout":30})
    client.API_URL = "https://api1.binance.com/api"
    client.ping()
    print("BINANCE CONNECTED VIA PROXY!")
    tg("✅ Timothy Bot Live - Proxy OK")
except Exception as e:
    print(f"Proxy fail {e}, trying direct api1")
    try:
        client = Client(API_KEY, API_SECRET)
        client.API_URL = "https://api1.binance.com/api"
        client.ping()
        print("BINANCE CONNECTED DIRECT")
    except Exception as e2:
        print(f"BINANCE FAILED {e2}")

if not client:
    while True:
        print("No client, waiting 60s")
        time.sleep(60)

client.RECV_WINDOW = 60000
holding = None
buy_price = 0

print("Starting RSI trading loop...")
while True:
    try:
        for symbol in SYMBOLS:
            klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_15MINUTE, limit=50)
            closes = [float(k[4]) for k in klines]
            rsi = get_rsi(closes)
            price = closes[-1]
            print(f"{symbol} RSI {rsi:.1f} Price {price}")

            if holding is None and rsi < 30:
                usdt = float(client.get_asset_balance(asset='USDT')['free'])
                if usdt > 10:
                    qty = math.floor((usdt*0.95 / price)*100000)/100000
                    if qty > 0:
                        client.order_market_buy(symbol=symbol, quantity=qty)
                        holding = symbol; buy_price = price
                        tg(f"BUY {symbol} @ {price} RSI {rsi:.1f}")
                        break

            if holding == symbol and rsi > 70:
                asset = symbol.replace("USDT","")
                bal = float(client.get_asset_balance(asset=asset)['free'])
                if bal > 0:
                    client.order_market_sell(symbol=symbol, quantity=bal)
                    tg(f"SELL {symbol} @ {price} Profit {(price-buy_price)/buy_price*100:.2f}%")
                    holding = None
                    break

        time.sleep(30)
    except Exception as e:
        print(f"Loop error {e}")
        time.sleep(15)
