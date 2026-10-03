import os, time, math, threading, requests
from flask import Flask
from dotenv import load_dotenv
load_dotenv()
from binance.client import Client

API_KEY = os.getenv("BINANCE_API","").strip()
API_SECRET = os.getenv("BINANCE_SECRET","").strip()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN","").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","").strip()
PROXY_URL = os.getenv("PROXY_URL","").strip()

SYMBOLS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT"]

app = Flask(__name__)
@app.route('/')
def home(): return "Bot checking proxy"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
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

proxies = {"http":PROXY_URL,"https":PROXY_URL} if PROXY_URL else None
tg(f"Testing proxy {PROXY_URL[:40]}...")

# Try with detailed error reporting
endpoints = ["https://api.binance.com/api","https://api1.binance.com/api","https://api2.binance.com/api","https://api3.binance.com/api","https://api-gcp.binance.com/api","https://api.binance.com"]

for base in endpoints:
    for use_proxy in [True, False]:
        try:
            rp = proxies if use_proxy else None
            c = Client(API_KEY, API_SECRET, requests_params={"proxies":rp,"timeout":15} if rp else {"timeout":15}, ping=False)
            c.API_URL = base
            c.RECV_WINDOW = 60000
            bal = c.get_asset_balance(asset='USDT')
            tg(f"✅ SUCCESS {base} proxy={use_proxy} USDT={bal}")
            print(f"SUCCESS {base} proxy={use_proxy}")
            # If success, start main bot loop
            market_client = Client(API_KEY, API_SECRET, requests_params={"timeout":15}, ping=False)
            market_client.API_URL = "https://data-api.binance.vision/api"
            holding=None; buy_price=0
            for sym in SYMBOLS:
                asset=sym.replace("USDT","")
                if asset=="USDT": continue
                try:
                    b=float(c.get_asset_balance(asset=asset)['free'])
                    if b>0.00001:
                        holding=sym
                        ticker=market_client.get_symbol_ticker(symbol=sym)
                        buy_price=float(ticker['price'])
                        tg(f"🔄 Found holding {sym} {b} @ ${buy_price}")
                        break
                except: pass
            # loop forever
            while True:
                time.sleep(30)
            break
        except Exception as e:
            msg = str(e)[:300]
            print(f"FAIL {base} proxy={use_proxy} {msg}")
            tg(f"❌ FAIL {base} proxy={use_proxy}: {msg}")
            time.sleep(2)

tg("❌ All endpoints failed. Proxy dead, need new proxy.")
