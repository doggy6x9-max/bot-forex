import os
import sys
import json
import logging
import requests
from datetime import datetime

# ==============================================================================
# CẤU HÌNH (DÙNG ĐỂ CHẠY THẬT)
# ==============================================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
FF_RSS_URL = "https://www.forexfactory.com/ffcal_week_this.xml"
STATE_FILE = "state.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

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
    # Code này chỉ chạy quét tin, không gửi tin nhắn rác
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(FF_RSS_URL, headers=headers, timeout=10)
        response.raise_for_status()
        logging.info("Đã quét tin thành công. Đang chờ tin quan trọng...")
    except Exception as e:
        logging.error(f"Lỗi: {e}")
        return
    save_state(state)

if __name__ == "__main__":
    run_bot()
