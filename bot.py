import os
import sys
import json
import logging
import requests
from datetime import datetime

# ==============================================================================
# CẤU HÌNH
# ==============================================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
FF_RSS_URL = "https://www.forexfactory.com/ffcal_week_this.xml"
STATE_FILE = "state.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=5)
    except:
        pass

def load_state():
    default_state = {"alerted": [], "checkpoints": []}
    if not os.path.exists(STATE_FILE): return default_state
    try:
        with open(STATE_FILE, "r") as f: return json.load(f)
    except: return default_state

def save_state(state):
    with open(STATE_FILE, "w") as f: json.dump(state, f, indent=4)

def run_bot():
    state = load_state()
    # Gửi tin nhắn test ngay khi bot chạy
    send_telegram("Bot đang chạy test thành công!")
    logging.info("Đã gửi tin test thành công.")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(FF_RSS_URL, headers=headers, timeout=10)
        response.raise_for_status()
        logging.info("Lấy dữ liệu RSS thành công.")
    except Exception as e:
        logging.error(f"Lỗi: {e}")
        return
    save_state(state)

if __name__ == "__main__":
    run_bot()
