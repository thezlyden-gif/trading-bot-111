
import requests
import time
from flask import Flask, request
from threading import Thread
from datetime import datetime

TOKEN = '8392693204:AAEDJvZhNvukxx4nnYDRZYrFyUo8PkQqIr8'
CHAT_ID = 7647937915
API_URL = f"https://api.telegram.org/bot{TOKEN}"
APP_URL = 'https://telegram-crypto-bot-imxi.onrender.com'
WEBHOOK_PATH = f'/{TOKEN}'
PRICE_UPDATE_INTERVAL = 60
SIGNAL_INTERVAL = 120

app = Flask(__name__)
prices = {}

monitored_symbols = [
    "BTC", "ETH", "SOL", "LINK", "OP", "ARB", "APT",
    "INJ", "FET", "RNDR", "DYDX", "LDO", "SEI", "BLUR"
]

def fetch_price(symbol):
    url = "https://api.bybit.com/v5/market/tickers?category=spot"
    try:
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()

        if "result" in data and "list" in data["result"]:
            for ticker in data["result"]["list"]:
                if ticker["symbol"] == f"{symbol}USDT":
                    return float(ticker["lastPrice"])
    except Exception as e:
        print(f"Ошибка получения цены {symbol}: {e}")
    return None

def update_prices():
    while True:
        for symbol in monitored_symbols:
            price = fetch_price(symbol)
            if price:
                prices[symbol] = price
        time.sleep(PRICE_UPDATE_INTERVAL)

def generate_signal():
    if not prices:
        return None
    entry = "BTC"
    price = prices.get(entry)
    if price:
        now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        return (f"📈 Сигнал на вход ({now})\n"
                f"Монета: {entry}\n"
                f"Тип: LONG\n"
                f"Цена входа: {price}$\n"
                f"Объём входа: 10% от депозита\n"
                f"Стоп-лосс: {price * 0.98:.2f}$\n"
                f"Тейк-профит: {price * 1.05:.2f}$")
    return None

def send_to_telegram(text):
    url = f"{API_URL}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

def auto_signal_loop():
    while True:
        try:
            signal = generate_signal()
            if signal:
                send_to_telegram(signal)
                print(f"✅ Сигнал отправлен: {signal[:50]}...")
            else:
                print("⛔ Сигнал не найден")
        except Exception as e:
            print(f"❌ Ошибка в автоанализе: {e}")
        time.sleep(SIGNAL_INTERVAL)

@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if text == "/start":
            send_to_telegram("Привет! Бот готов к работе.")
        elif text == "/price":
            out = "📊 Актуальные цены:\n"
            for sym in monitored_symbols:
                price = prices.get(sym, "—")
                out += f"{sym}: ${price}\n"
            send_to_telegram(out)
        elif text == "/signal":
            signal = generate_signal()
            if signal:
                send_to_telegram(signal)
            else:
                send_to_telegram("Нет актуального сигнала.")
        elif text == "/help":
            out = ("📘 Доступные команды:\n"
                   "/price — текущие цены\n"
                   "/signal — получить сигнал\n"
                   "/help — команды\n")
            send_to_telegram(out)

    return {"ok": True}

def set_webhook():
    url = f"{API_URL}/setWebhook"
    webhook_url = f"{APP_URL}{WEBHOOK_PATH}"
    res = requests.post(url, json={"url": webhook_url})
    print(f"Webhook установлен: {res.json()}")

if __name__ == "__main__":
    Thread(target=update_prices).start()
    Thread(target=auto_signal_loop).start()
    set_webhook()
    app.run(host="0.0.0.0", port=10000)
