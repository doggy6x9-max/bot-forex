import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
# URL Proxy trung gian (đã test chạy ngon)
URL = "https://api.allorigins.win/raw?url=https://www.forexfactory.com/ffcal_week_this.xml"

def send(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except: pass

def run():
    try:
        data = requests.get(URL, timeout=20).content
        root = ET.fromstring(data)
        now = datetime.now() + timedelta(hours=7) # Giờ Việt Nam
        
        # 1. BÁO CÁO ĐỊNH KỲ (5h, 12h, 17h) - Gửi 1 lần duy nhất trong khung giờ
        if now.minute < 10 and now.hour in [5, 12, 17]:
            msg = f"📅 <b>BÁO CÁO PHIÊN {now.hour}H:00</b>\n"
            found = False
            for e in root.findall('event'):
                # Kiểm tra ngày và là tin Đỏ (High)
                if e.find('date').text in now.strftime('%a %b %d') and e.find('impact').text == 'High':
                    msg += f"• {e.find('time').text}: {e.find('title').text}\n"
                    found = True
            if found: send(msg)
            else: send(f"✅ Hôm nay phiên {now.hour}h không có tin Đỏ.")

        # 2. CẢNH BÁO TIN ĐỎ TRƯỚC 10 PHÚT
        for e in root.findall('event'):
            if e.find('impact').text == 'High':
                try:
                    tin_str = f"{now.year} {e.find('date').text} {e.find('time').text}"
                    tin_time = datetime.strptime(tin_str, '%Y %a %b %d %I:%M%p')
                    # Nếu tin rơi vào khoảng từ 1 phút đến 10 phút tới
                    if 0 < (tin_time - now).total_seconds() <= 600:
                        send(f"🔥 <b>CẢNH BÁO:</b> {e.find('title').text} ra sau 10 phút nữa!")
                except: continue
    except: pass

if __name__ == "__main__":
    run()
