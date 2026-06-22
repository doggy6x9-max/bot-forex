import os
import sys
import json
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date
import pytz

# ==============================================================================
# CẤU HÌNH
# ==============================================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
FF_RSS_URL = "https://www.forexfactory.com/ffcal_week_this.xml"
STATE_FILE = "state.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"alerted": [], "checkpoints": []}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, data=payload)

def fetch_news():
    # Thêm headers để giả dạng trình duyệt, tránh lỗi 403 Forbidden
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(FF_RSS_URL, headers=headers, timeout=10)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logging.error(f"Fetch RSS lỗi: {e}")
        return None

def run_bot():
    state = load_state()
    logging.info(f"Đã load state: {len(state['alerted'])} alerted, {len(state['checkpoints'])} checkpoints.")
    logging.info(f"▶ Run lúc {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    xml_data = fetch_news()
    if not xml_data:
        logging.warning("Không lấy được dữ liệu RSS. Bỏ qua lần này.")
        return

    # Xử lý nội dung RSS (phần logic phân tích tin tức ở đây)
    # ... (Giữ nguyên logic xử lý tin tức của anh)

    logging.info("Đã lưu state.json.")
    save_state(state)
    logging.info("✅ Bot hoàn thành.")

if __name__ == "__main__":
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logging.error("TELEGRAM_TOKEN hoặc CHAT_ID chưa set. Thoát.")
        sys.exit(1)
    run_bot()
