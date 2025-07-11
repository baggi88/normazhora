from flask import Flask
from threading import Thread
import logging
import os
from datetime import datetime

# Отключаем логи Flask
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def home():
    return f"Бот работает! Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

@app.route('/status')
def status():
    return {
        "status": "online",
        "uptime": str(datetime.now() - start_time),
        "last_check": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    global start_time
    start_time = datetime.now()
    server = Thread(target=run)
    server.daemon = True  # Поток завершится вместе с основной программой
    server.start()
    print(f"Сервер запущен на порту {os.environ.get('PORT', 8080)}") 