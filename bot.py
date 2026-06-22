import os
import sys
import json
import logging
import requests
from datetime import datetime

# ==============================================================================
# CẤU HÌNH BOT (ĐÃ FIX LỖI 403)
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
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        logging.error(f"Lỗi Telegram: {e}")

def run_bot():
    # Giả lập trình duyệt Chrome mới nhất, đầy đủ thông số để tránh bị chặn 403
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    }
    
    try:
        # Thử lấy dữ liệu
        response = requests.get(FF_RSS_URL, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Nếu thành công
        logging.info("Quét dữ liệu thành công.")
        send_telegram("✅ <b>QUÉT DỮ LIỆU THÀNH CÔNG!</b>\nBot đã vượt qua hàng rào bảo mật và lấy được tin mới từ ForexFactory.")
        
    except Exception as e:
        # Nếu vẫn bị 403, báo lỗi cụ thể để mình biết
        error_msg = f"❌ <b>LỖI QUÉT TIN:</b>\n{str(e)}"
        logging.error(error_msg)
        send_telegram(error_msg)

if __name__ == "__main__":
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logging.error("Thiếu Token hoặc Chat ID!")
        sys.exit(1)
    run_bot()
