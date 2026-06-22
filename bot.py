import os
import sys
import json
import logging
import requests
from datetime import datetime

# ==============================================================================
# CẤU HÌNH BOT
# ==============================================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
FF_RSS_URL = "https://www.forexfactory.com/ffcal_week_this.xml"
STATE_FILE = "state.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def send_telegram(message):
    """Gửi tin nhắn vào Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        logging.error(f"Lỗi gửi Telegram: {e}")

def run_bot():
    """Hàm chạy chính của bot"""
    # 1. GỬI TIN TEST NGAY KHI CHẠY (Để anh biết bot đã sống)
    send_telegram("🔔 <b>BOT ĐANG CHẠY TEST:</b>\n\n<b>Trạng thái:</b> Đang quét dữ liệu thực tế...\n<i>Anh kiểm tra xem bot đã kết nối tốt chưa nhé!</i>")
    
    # 2. QUÉT DỮ LIỆU THẬT
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(FF_RSS_URL, headers=headers, timeout=10)
        response.raise_for_status()
        
        # In log để anh xem trên GitHub
        logging.info("Đã quét dữ liệu từ ForexFactory thành công.")
        send_telegram("✅ <b>QUÉT DỮ LIỆU THÀNH CÔNG!</b>\nBot đã kết nối với ForexFactory và đang chờ tin đỏ.")
        
    except Exception as e:
        logging.error(f"Lỗi quét tin: {e}")
        send_telegram(f"❌ <b>LỖI QUÉT TIN:</b>\n{e}")

if __name__ == "__main__":
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logging.error("Chưa cài đặt Telegram Token hoặc Chat ID!")
        sys.exit(1)
    run_bot()
