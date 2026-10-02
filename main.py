from binance.client import Client
import time, math, requests, os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("BINANCE_API")
API_SECRET = os.getenv("BINANCE_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT","DOTUSDT","MATICUSDT","LINKUSDT","LTCUSDT","TRXUSDT","ETCUSDT","FILUSDT","UNIUSDT","ATOMUSDT","NEARUSDT","APTUSDT","ARBUSDT"]
TAKE_PROFIT = 2.5
STOP_LOSS = 4.0
MIN_TRADE = 2.0

def tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=5)
        print(f"TG: {msg}")
    except Exception as e:
        print(f"TG error {e}")

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

client = Client(API_KEY, API_SECRET)
client.RECV_WINDOW = 60000
print("Connected to Binance!")

holding = None
buy_price = 0
try:
    acc = client.get_account()
    for b in acc['balances']:
        asset = b['asset']
        total = float(b['free'])+float(b['locked'])
        if total > 0 and asset not in ["USDT","BNB"]:
            symbol = asset+"USDT"
            try:
                trades = client.get_my_trades(symbol=symbol, limit=10)
                if trades:
                    tq = sum(float(t['qty']) for t in trades if t['isBuyer'])
                    tc = sum(float(t['qty'])*float(t['price']) for t in trades if t['isBuyer'])
                    buy_price = tc/tq if tq>0 else float(client.get_symbol_ticker(symbol=symbol)['price'])
                holding = symbol
                print(f"FOUND HOLDING: {holding} avg=${buy_price:.2f}")
                tg(f"Restart - Holding {holding} ${buy_price:.2f}")
                break
            except: pass
except Exception as e:
    print(f"balance error {e}")

if not holding:
    print(f"BOT STARTED - No holding - MIN ${MIN_TRADE} no MAX")
    tg(f"Bot started - USDT check")

while True:
    try:
        usdt_bal = float(client.get_asset_balance(asset='USDT')['free'])
        trade_amount = usdt_bal * 0.95 if usdt_bal > MIN_TRADE*2 else usdt_bal
        if holding is None:
            best = None
            best_rsi = 100
            for symbol in SYMBOLS:
                try:
                    kl = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1HOUR, limit=30)
                    closes = [float(k[4]) for k in kl]
                    rsi = get_rsi(closes)
                    print(f"{symbol} RSI {rsi:.1f}")
                    if rsi < best_rsi and rsi < 35:
                        best_rsi = rsi
                        best = symbol
                except: pass
            if best and trade_amount >= MIN_TRADE:
                print(f"BUY SIGNAL {best} RSI {best_rsi:.1f} amount ${trade_amount:.2f}")
                info = client.get_symbol_info(best)
                step = float([f for f in info['filters'] if f['filterType']=='LOT_SIZE'][0]['stepSize'])
                prec = int(round(-math.log(step,10),0))
                price = float(client.get_symbol_ticker(symbol=best)['price'])
                qty = math.floor((trade_amount/price) * (10**prec)) / (10**prec)
                if qty>0:
                    client.order_market_buy(symbol=best, quantity=qty)
                    holding=best
                    buy_price=price
                    tg(f"BUY {best} RSI {best_rsi:.1f} Price ${price} Amount ${trade_amount:.2f}")
            else:
                print(f"No signal - Best {best} - USDT ${usdt_bal:.2f} - wait 30s")
                time.sleep(30)
        else:
            price = float(client.get_symbol_ticker(symbol=holding)['price'])
            profit = ((price-buy_price)/buy_price)*100
            print(f"HOLDING {holding} | ${price:.4f} | Buy ${buy_price:.4f} | {profit:.2f}%")
            if profit >= TAKE_PROFIT or profit <= -STOP_LOSS:
                asset = holding.replace("USDT","")
                bal = float(client.get_asset_balance(asset=asset)['free'])
                info = client.get_symbol_info(holding)
                step = float([f for f in info['filters'] if f['filterType']=='LOT_SIZE'][0]['stepSize'])
                prec = int(round(-math.log(step,10),0))
                bal = math.floor(bal * (10**prec)) / (10**prec)
                if bal>0:
                    client.order_market_sell(symbol=holding, quantity=bal)
                    tg(f"{'SOLD PROFIT' if profit>=0 else 'STOP LOSS'} {holding} {profit:.2f}% Price ${price}")
                holding=None
                buy_price=0
                time.sleep(5)
        time.sleep(5)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)
