from binance.client import Client
import time, math, requests, os, threading
from flask import Flask
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("BINANCE_API") or os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_SECRET") or os.getenv("BINANCE_API_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PROXY_URL = os.getenv("PROXY_URL") or "http://pjaaqimr:alt6s2a3hin@31.59.20.176:6754"

SYMBOLS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT","DOTUSDT","MATICUSDT","LINKUSDT","LTCUSDT","TRXUSDT","ETCUSDT","FILUSDT","UNIUSDT","ATOMUSDT","NEARUSDT","APTUSDT","ARBUSDT"]

app = Flask(__name__)
@app.route('/')
def home(): return "OK"
def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
threading.Thread(target=run_web, daemon=True).start()

def tg(m):
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": m}, timeout=10)
    except: pass

def get_rsi(c,p=14):
    if len(c)<p+1: return 50
    d=[c[i]-c[i-1] for i in range(1,len(c))]
    g=[max(0,x) for x in d[-p:]]; l=[max(0,-x) for x in d[-p:]]
    ag=sum(g)/p; al=sum(l)/p
    if al==0: return 80
    return 100-(100/(1+ag/al))

print("Starting bot...")
try:
    print("Trying proxy...")
    client = Client(API_KEY, API_SECRET, requests_params={"proxies":{"http":PROXY_URL,"https":PROXY_URL},"timeout":30})
    client.API_URL="https://api1.binance.com/api"
    client.ping()
    print("Proxy OK!")
except Exception as e:
    print(f"Proxy failed {e}, trying direct...")
    client = Client(API_KEY, API_SECRET)
    for ep in ["https://api1.binance.com","https://api2.binance.com","https://api3.binance.com"]:
        try:
            client.API_URL=ep+"/api"
            client.ping()
            print(f"Connected {ep}")
            break
        except: continue

client.RECV_WINDOW=60000
print("Connected!")

# --- YOUR ORIGINAL TRADING LOOP (same) ---
holding=None; buy_price=0
try:
    acc=client.get_account()
    for b in acc['balances']:
        tot=float(b['free'])+float(b['locked'])
        if tot>0 and b['asset'] not in ["USDT","BNB"]:
            sym=b['asset']+"USDT"
            try:
                tr=client.get_my_trades(symbol=sym,limit=10)
                if tr:
                    tq=sum(float(t['qty']) for t in tr if t['isBuyer'])
                    tc=sum(float(t['qty'])*float(t['price']) for t in tr if t['isBuyer'])
                    buy_price=tc/tq if tq>0 else float(client.get_symbol_ticker(symbol=sym)['price'])
                holding=sym
                print(f"HOLDING {holding} {buy_price}")
                break
            except: pass
except Exception as e: print(e)

if not holding:
    tg("Bot started OK")

while True:
    try:
        usdt=float(client.get_asset_balance(asset='USDT')['free'])
        amt=usdt*0.95 if usdt>4 else usdt
        if holding is None:
            best=None; brsi=100
            for s in SYMBOLS:
                try:
                    kl=client.get_klines(symbol=s, interval=Client.KLINE_INTERVAL_1HOUR, limit=30)
                    closes=[float(k[4]) for k in kl]
                    rsi=get_rsi(closes)
                    print(f"{s} {rsi:.1f}")
                    if rsi<brsi and rsi<35:
                        brsi=rssi if False else rsi; best=s
                except: pass
            if best and amt>=2:
                info=client.get_symbol_info(best)
                step=float([f for f in info['filters'] if f['filterType']=='LOT_SIZE'][0]['stepSize'])
                prec=int(round(-math.log(step,10),0))
                price=float(client.get_symbol_ticker(symbol=best)['price'])
                qty=math.floor((amt/price)*(10**prec))/(10**prec)
                if qty>0:
                    client.order_market_buy(symbol=best, quantity=qty)
                    holding=best; buy_price=price
                    tg(f"BUY {best} RSI {brsi:.1f} ${price}")
            else:
                print(f"No signal USDT {usdt:.2f}"); time.sleep(30)
        else:
            price=float(client.get_symbol_ticker(symbol=holding)['price'])
            profit=((price-buy_price)/buy_price)*100
            print(f"HOLD {holding} {profit:.2f}%")
            if profit>=2.5 or profit<=-4.0:
                asset=holding.replace("USDT","")
                bal=float(client.get_asset_balance(asset=asset)['free'])
                info=client.get_symbol_info(holding)
                step=float([f for f in info['filters'] if f['filterType']=='LOT_SIZE'][0]['stepSize'])
                prec=int(round(-math.log(step,10),0))
                bal=math.floor(bal*(10**prec))/(10**prec)
                if bal>0:
                    client.order_market_sell(symbol=holding, quantity=bal)
                    tg(f"SELL {holding} {profit:.2f}%")
                holding=None; buy_price=0
        time.sleep(5)
    except Exception as e:
        print(f"Error {e}"); time.sleep(10)
