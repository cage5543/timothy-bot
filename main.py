import os, time, math, threading, requests
from binance.client import Client
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
def home(): return "Bot OK"
def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
threading.Thread(target=run_web, daemon=True).start()

def tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
    except: pass

def get_rsi(closes, p=14):
    if len(closes) < p+1: return 50
    deltas = [closes[i]-closes[i-1] for i in range(1,len(closes))]
    gains = [max(0,d) for d in deltas[-p:]]
    losses = [max(0,-d) for d in deltas[-p:]]
    avg_gain = sum(gains)/p
    avg_loss = sum(losses)/p
    if avg_loss == 0: return 80
    rs = avg_gain/avg_loss
    return 100 - (100/(1+rs))

print("Starting...")
try:
    print(f"Trying proxy {PROXY_URL[:20]}...")
    client = Client(API_KEY, API_SECRET, requests_params={"proxies":{"http":PROXY_URL,"https":PROXY_URL}})
    client.API_URL = "https://api1.binance.com/api"
    client.ping()
    print("Proxy connected!")
except Exception as e:
    print(f"Proxy failed: {e}")
    client = Client(API_KEY, API_SECRET)
    client.API_URL = "https://api1.binance.com/api"
    try:
        client.ping()
        print("Direct api1 connected!")
    except Exception as e2:
        print(f"Direct also failed: {e2}")

client.RECV_WINDOW = 60000
holding = None
buy_price = 0

try:
    acc = client.get_account()
    for b in acc['balances']:
        total = float(b['free'])+float(b['locked'])
        if total>0 and b['asset'] not in ["USDT","BNB"]:
            symbol = b['asset']+"USDT"
            holding = symbol
            try:
                price = float(client.get_symbol_ticker(symbol=symbol)['price'])
                buy_price = price
            except: buy_price = 0
            print(f"Found holding {holding}")
            break
except Exception as e:
    print(f"Account error: {e}")

tg("Bot started - Render fixed")

while True:
    try:
        usdt = float(client.get_asset_balance(asset='USDT')['free'])
        trade_amount = usdt*0.95 if usdt>4 else usdt

        if holding is None:
            best = None
            best_rsi = 100
            for sym in SYMBOLS:
                try:
                    kl = client.get_klines(symbol=sym, interval=Client.KLINE_INTERVAL_1HOUR, limit=30)
                    closes = [float(k[4]) for k in kl]
                    rsi = get_rsi(closes)
                    print(f"{sym} RSI {rsi:.1f}")
                    if rsi < best_rsi and rsi < 35:
                        best_rsi = rsi
                        best = sym
                except: pass

            if best and trade_amount >= 2:
                info = client.get_symbol_info(best)
                step = float([f for f in info['filters'] if f['filterType']=='LOT_SIZE'][0]['stepSize'])
                prec = int(round(-math.log(step,10),0))
                price = float(client.get_symbol_ticker(symbol=best)['price'])
                qty = math.floor((trade_amount/price)*(10**prec))/(10**prec)
                if qty>0:
                    client.order_market_buy(symbol=best, quantity=qty)
                    holding=best
                    buy_price=price
                    tg(f"BUY {best} RSI {best_rsi:.1f} ${price}")
            else:
                print(f"No signal USDT {usdt:.2f}")
                time.sleep(30)
        else:
            price = float(client.get_symbol_ticker(symbol=holding)['price'])
            profit = ((price-buy_price)/buy_price)*100 if buy_price>0 else 0
            print(f"HOLD {holding} {profit:.2f}%")
            if profit>=2.5 or profit<=-4.0:
                asset = holding.replace("USDT","")
                bal = float(client.get_asset_balance(asset=asset)['free'])
                info = client.get_symbol_info(holding)
                step = float([f for f in info['filters'] if f['filterType']=='LOT_SIZE'][0]['stepSize'])
                prec = int(round(-math.log(step,10),0))
                bal = math.floor(bal*(10**prec))/(10**prec)
                if bal>0:
                    client.order_market_sell(symbol=holding, quantity=bal)
                    tg(f"SELL {holding} {profit:.2f}%")
                holding=None
                buy_price=0
        time.sleep(5)
    except Exception as e:
        print(f"Loop error: {e}")
        time.sleep(10)
