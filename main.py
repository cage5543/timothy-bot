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
PROFIT_TARGET = 0.025  # 2.5% SELL
RSI_BUY = 30           # BUY when RSI < 30
MIN_USDT = 2           # Minimum $2 to buy, no maximum

app = Flask(__name__)
@app.route('/')
def home(): return f"Timothy Bot LIVE - Sell +{PROFIT_TARGET*100}% Buy RSI<{RSI_BUY} Min ${MIN_USDT}"
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
            c=Client(API_KEY, API_SECRET, requests_params={"proxies":proxies,"timeout":30} if proxies else {"timeout":30}, ping=False)
            c.API_URL=base
            c.ping()
            print(f"BINANCE CONNECTED {base}")
            tg(f"✅ Connected {base}")
            return c
        except Exception as e:
            print(f"{base} fail {e}")
            time.sleep(2)
    return None

print(f"=== BOOTING BOT - SELL +{PROFIT_TARGET*100}% MIN BUY ${MIN_USDT} ===")
client=make_client()
while not client:
    time.sleep(300)
    client=make_client()

client.RECV_WINDOW=60000

# AUTO-DETECT WHAT YOU HOLD
holding = None
buy_price = 0
try:
    for sym in SYMBOLS:
        asset = sym.replace("USDT","")
        if asset == "USDT": continue
        bal = float(client.get_asset_balance(asset=asset)['free'])
        if bal > 0.00001:
            holding = sym
            try:
                trades = client.get_my_trades(symbol=sym, limit=10)
                last_buy = [t for t in trades if t['isBuyer']][-1]
                buy_price = float(last_buy['price'])
            except:
                ticker = client.get_symbol_ticker(symbol=sym)
                buy_price = float(ticker['price'])
            tg(f"🔄 Found holding {sym} {bal} @ ${buy_price:.4f}, will sell at +{PROFIT_TARGET*100}% (${buy_price*(1+PROFIT_TARGET):.4f})")
            print(f"Found holding {sym} buy@{buy_price}")
            break
    if not holding:
        tg(f"💤 No holding found. Waiting for RSI<{RSI_BUY} to BUY min ${MIN_USDT}")
except Exception as e:
    print(f"Detect err {e}")

print(f"Trading loop start holding={holding} buy={buy_price}")

while True:
    try:
        for sym in SYMBOLS:
            klines=client.get_klines(symbol=sym, interval=Client.KLINE_INTERVAL_15MINUTE, limit=50)
            closes=[float(k[4]) for k in klines]
            rsi=get_rsi(closes)
            price=closes[-1]

            # SELL LOGIC +2.5%
            if holding == sym:
                target_price = buy_price * (1 + PROFIT_TARGET)
                pnl = ((price - buy_price) / buy_price * 100) if buy_price else 0
                print(f"HOLDING {sym} buy {buy_price:.4f} now {price:.4f} PnL {pnl:.2f}% target {target_price:.4f} RSI {rsi:.1f}")
                if price >= target_price:
                    asset=sym.replace("USDT","")
                    bal=float(client.get_asset_balance(asset=asset)['free'])
                    if bal>0:
                        client.order_market_sell(symbol=sym, quantity=bal)
                        tg(f"💰 SOLD {sym} @ ${price:.4f} (Buy was ${buy_price:.4f}) Profit +{pnl:.2f}%")
                        holding=None
                        buy_price=0
                continue

            # BUY LOGIC - Min $2, No Max, RSI<30
            if holding is None:
                usdt=float(client.get_asset_balance(asset='USDT')['free'])
                if rsi < RSI_BUY and usdt >= MIN_USDT:
                    # Use 95% of all USDT (no max)
                    buy_usdt = usdt * 0.95
                    qty=math.floor((buy_usdt/price)*100000)/100000
                    if qty>0:
                        client.order_market_buy(symbol=sym, quantity=qty)
                        holding=sym
                        buy_price=price
                        tg(f"🟢 BUY {sym} @ ${price:.4f} RSI {rsi:.1f} using ${buy_usdt:.2f} | Target sell ${price*(1+PROFIT_TARGET):.4f} (+{PROFIT_TARGET*100}%)")
                        break
                else:
                    print(f"{sym} RSI {rsi:.1f} USDT {usdt:.2f}")

        time.sleep(30)
    except Exception as e:
        print(f"Loop err {e}")
        time.sleep(20)
