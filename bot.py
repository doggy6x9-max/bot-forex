import os
import requests
import xml.etree.ElementTree as ET

def send_telegram(message):
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
    CHAT_ID = os.environ.get("CHAT_ID", "")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"})

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
response = requests.get("https://www.forexfactory.com/ffcal_week_this.xml", headers=headers)
root = ET.fromstring(response.content)

# Lấy 3 tin đầu tiên trong danh sách để anh xem nó quét được gì
msg = "🔍 <b>KẾT QUẢ QUÉT DỮ LIỆU THỰC TẾ:</b>\n\n"
for event in root.findall('event')[:3]:
    title = event.find('title').text
    impact = event.find('impact').text
    date = event.find('date').text
    msg += f"• <b>{title}</b>\n  Tác động: {impact}\n  Ngày: {date}\n\n"

send_telegram(msg)
