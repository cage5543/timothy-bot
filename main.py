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
PROFIT_TARGET = 0.025
RSI_BUY = 30
MIN_USDT = 2

app = Flask(__name__)
@app.route('/')
def home(): return "Timothy Bot LIVE"
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

def make_client():
    proxies={"http":PROXY_URL,"https":PROXY_URL} if PROXY_URL else None
    for base in ["https://data-api.binance.vision/api","https://api1.binance.com/api","https://api2.binance.com/api"]:
        try:
            c=Client(API_KEY, API_SECRET, requests_params={"proxies":proxies,"timeout":30} if proxies else {"timeout":30}, ping=False)
            c.API_URL=base; c.ping()
            print(f"BINANCE CONNECTED {base}"); tg(f"✅ Connected {base}")
            return c
        except Exception as e: print(f"{base} fail {e}"); time.sleep(2)
    return None

print("=== BOOTING SAFE VERSION ===")
client=make_client()
while not client:
    time.sleep(60); client=make_client()
client.RECV_WINDOW=60000

holding=None; buy_price=0
print("Checking balances...")
for sym in SYMBOLS:
    try:
        asset=sym.replace("USDT","")
        if asset=="USDT": continue
        bal_data=client.get_asset_balance(asset=asset)
        bal=float(bal_data['free'])+float(bal_data['locked'])
        print(f"Balance {asset}: {bal}")
        if bal>0.00001:
            holding=sym
            ticker=client.get_symbol_ticker(symbol=sym)
            buy_price=float(ticker['price'])
            tg(f"🔄 Found holding {sym} {bal} @ ${buy_price:.4f} -> Sell target ${buy_price*1.025:.4f} (+2.5%)")
            break
    except Exception as e:
        print(f"Balance check {sym} err {e}")
        tg(f"⚠️ Balance check {sym} error {e}")

if not holding:
    tg(f"💤 No coin holding. USDT ready. Will BUY when RSI<{RSI_BUY} min ${MIN_USDT}")

print(f"Start loop holding={holding} buy={buy_price}")

while True:
    try:
        for sym in SYMBOLS:
            klines=client.get_klines(symbol=sym, interval=Client.KLINE_INTERVAL_15MINUTE, limit=50)
            closes=[float(k[4]) for k in klines]
            rsi=get_rsi(closes); price=closes[-1]

            if holding==sym:
                target=buy_price*1.025
                pnl=((price-buy_price)/buy_price*100) if buy_price else 0
                print(f"HOLDING {sym} {price:.3f} PnL {pnl:.2f}% target {target:.3f} RSI {rsi:.1f}")
                if price>=target:
                    asset=sym.replace("USDT",""); bal=float(client.get_asset_balance(asset=asset)['free'])
                    if bal>0:
                        client.order_market_sell(symbol=sym, quantity=bal)
                        tg(f"💰 SOLD {sym} @ ${price:.4f} Profit +{pnl:.2f}%")
                        holding=None; buy_price=0
                continue

            if holding is None:
                usdt=float(client.get_asset_balance(asset='USDT')['free'])
                if rsi<RSI_BUY and usdt>=MIN_USDT:
                    qty=math.floor((usdt*0.95/price)*100000)/100000
                    if qty>0:
                        client.order_market_buy(symbol=sym, quantity=qty)
                        holding=sym; buy_price=price
                        tg(f"🟢 BUY {sym} @ ${price:.4f} RSI {rsi:.1f} Target ${price*1.025:.4f}")
                        break
        time.sleep(30)
    except Exception as e:
        print(f"Loop err {e}"); tg(f"Loop err {e}"); time.sleep(20)
