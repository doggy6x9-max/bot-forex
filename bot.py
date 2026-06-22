import os
import requests
import logging

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
FF_RSS_URL = "https://www.forexfactory.com/ffcal_week_this.xml"

# Sử dụng một dịch vụ Proxy trung gian miễn phí để vượt chặn
PROXY_URL = "https://api.allorigins.win/raw?url=" + FF_RSS_URL

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"})

def run_bot():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36'}
    try:
        # Bot sẽ truy cập qua Proxy trung gian, ForexFactory sẽ không biết là từ GitHub
        response = requests.get(PROXY_URL, headers=headers, timeout=20)
        response.raise_for_status()
        
        # Nếu vào đến đây là thành công
        send_telegram("✅ <b>VƯỢT RÀO THÀNH CÔNG!</b>\nBot đã lấy được dữ liệu tin tức qua Proxy.")
    except Exception as e:
        send_telegram(f"❌ <b>VẪN LỖI:</b> {str(e)}")

if __name__ == "__main__":
    run_bot()
