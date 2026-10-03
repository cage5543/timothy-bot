import os, time, math, threading, requests
from flask import Flask
from dotenv import load_dotenv
load_dotenv()
from binance.client import Client

API_KEY = os.getenv("BINANCE_API","")
API_SECRET = os.getenv("BINANCE_SECRET","")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN","")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","")
PROXY_URL = os.getenv("PROXY_URL","")

SYMBOLS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT"]

app = Flask(__name__)
@app.route('/')
def home(): return "Timothy Bot LIVE"
def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
threading.Thread(target=run_web, daemon=True).start()

def tg(m):
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id":TELEGRAM_CHAT_ID,"text":m}, timeout=10)
    except: pass

def get_rsi(closes, p=14):
    if len(closes)<p+1: return 50
    deltas=[closes[i]-closes[i-1] for i in range(1,len(closes))]
    gains=[max(0,d) for d in deltas[-p:]]
    losses=[max(0,-d) for d in deltas[-p:]]
    ag=sum(gains)/p; al=sum(losses)/p
    if al==0: return 80
    return 100-(100/(1+ag/al))

def make_client():
    proxies={"http":PROXY_URL,"https":PROXY_URL} if PROXY_URL else None
    for base in ["https://data-api.binance.vision/api","https://api1.binance.com/api","https://api2.binance.com/api","https://api3.binance.com/api"]:
        try:
            print(f"Trying {base} proxy={bool(proxies)}")
            c=Client(API_KEY, API_SECRET, requests_params={"proxies":proxies,"timeout":30} if proxies else {"timeout":30}, ping=False)
            c.API_URL=base
            c.ping()
            print(f"BINANCE CONNECTED {base}")
            tg(f"✅ Connected {base}")
            return c
        except Exception as e:
            print(f"{base} fail {e}")
            time.sleep(3)
    return None

print("=== BOOTING ANTI-BAN BOT ===")
client=make_client()
if not client:
    print("All APIs banned, waiting 10min")
    while True:
        time.sleep(600)
        client=make_client()
        if client: break

client.RECV_WINDOW=60000
holding=None
print("Trading loop start")
while True:
    try:
        for sym in SYMBOLS:
            klines=client.get_klines(symbol=sym, interval=Client.KLINE_INTERVAL_15MINUTE, limit=50)
            closes=[float(k[4]) for k in klines]
            rsi=get_rsi(closes)
            price=closes[-1]
            print(f"{sym} RSI {rsi:.1f} {price}")
            if holding is None and rsi<30:
                usdt=float(client.get_asset_balance(asset='USDT')['free'])
                if usdt>12:
                    qty=math.floor((usdt*0.95/price)*100000)/100000
                    client.order_market_buy(symbol=sym, quantity=qty)
                    holding=sym
                    tg(f"BUY {sym} RSI {rsi:.1f}")
                    break
            if holding==sym and rsi>70:
                asset=sym.replace("USDT","")
                bal=float(client.get_asset_balance(asset=asset)['free'])
                if bal>0:
                    client.order_market_sell(symbol=sym, quantity=bal)
                    tg(f"SELL {sym} RSI {rsi:.1f}")
                    holding=None
                    break
        time.sleep(30)
    except Exception as e:
        print(f"Loop err {e}")
        time.sleep(20)
