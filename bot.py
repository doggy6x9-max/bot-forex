import os
import sys
import json
import logging
import requests
from datetime import datetime

# ==============================================================================
# BẢN TEST: ÉP BOT GỬI TIN MẪU
# ==============================================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, data=payload)

# Gửi tin demo để anh thấy giao diện
send_telegram("🔔 <b>TEST GIAO DIỆN BOT</b>\n\n<b>Tin:</b> USD - Non-Farm Employment\n<b>Tác động:</b> HIGH IMPACT (TIN ĐỎ)\n<b>Thời gian:</b> 19:30 (VN)\n\n<i>Bot đã sẵn sàng quét tin thực tế!</i>")
print("Đã gửi tin test.")
