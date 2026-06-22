"""
ForexFactory High-Impact News Alert Bot  ──  v3.0 (GitHub Actions)
===================================================================
Kiến trúc: One-shot stateless
  • Mỗi lần GitHub Actions trigger → script chạy 1 lần rồi thoát
  • State (alerted_events, sent_checkpoints) lưu vào state.json
  • Workflow tự git commit state.json sau mỗi lần chạy
  • Không cần server, không cần PythonAnywhere

Cách dùng:
  python bot.py

Environment variables (đặt trong GitHub Secrets):
  TELEGRAM_TOKEN   Token của Telegram Bot
  CHAT_ID          Chat ID nhận thông báo
"""

import os
import sys
import json
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date
import pytz

# ============================================================
# CẤU HÌNH
# ============================================================
TELEGRAM_TOKEN    = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID           = os.environ.get("CHAT_ID", "")
FF_RSS_URL        = "https://www.forexfactory.com/ffcal_week_this.xml"
STATE_FILE        = "state.json"

TIMEZONE          = pytz.timezone("Asia/Ho_Chi_Minh")   # GMT+7
ET_ZONE           = pytz.timezone("America/New_York")    # ForexFactory dùng ET

ALERT_BEFORE_MIN  = 10   # phút cảnh báo trước tin đỏ
ALERT_WINDOW_MIN  = 12   # quét trong cửa sổ [10, 12] phút để không bỏ sót

MORNING_HOUR      = 5
NOON_HOUR         = 12
EVENING_HOUR      = 17
CHECKPOINT_WINDOW = 9    # phút: gửi checkpoint nếu trong [H:00, H:09]

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ============================================================
# STATE PERSISTENCE  (đọc/ghi state.json)
# ============================================================
def load_state() -> dict:
    """
    Đọc state.json từ disk.
    Trả về dict rỗng nếu file không tồn tại hoặc bị lỗi.
    Schema:
      {
        "alerted_events":   ["event_id_1", ...],
        "sent_checkpoints": ["2026-06-22_0500", ...],
        "last_updated":     "2026-06-22T19:30:00+07:00"
      }
    """
    if not os.path.exists(STATE_FILE):
        log.info("state.json chưa tồn tại → khởi tạo state mới.")
        return {"alerted_events": [], "sent_checkpoints": []}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        log.info(
            "Đã load state: %d alerted, %d checkpoints.",
            len(state.get("alerted_events", [])),
            len(state.get("sent_checkpoints", [])),
        )
        return state
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Đọc state.json lỗi (%s) → reset state.", e)
        return {"alerted_events": [], "sent_checkpoints": []}


def save_state(state: dict) -> None:
    """Ghi state ra state.json."""
    state["last_updated"] = datetime.now(TIMEZONE).isoformat()
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        log.info("Đã lưu state.json.")
    except OSError as e:
        log.error("Ghi state.json lỗi: %s", e)


def cleanup_old_state(state: dict, today: date) -> dict:
    """
    Xóa các entries của ngày cũ hơn hôm nay khỏi state
    để tránh file phình to theo thời gian.
    alerted_events dùng pattern: "COUNTRY_TITLE_DATE_TIME"
    sent_checkpoints dùng pattern: "YYYY-MM-DD_HHMM"
    """
    today_str = today.strftime("%Y-%m-%d")

    # Giữ lại checkpoints của hôm nay
    state["sent_checkpoints"] = [
        k for k in state.get("sent_checkpoints", [])
        if k.startswith(today_str)
    ]

    # alerted_events: giữ lại nếu date_s trong key chứa tháng/năm hôm nay
    # Key format: "CAD_CPI_Mon Jun 22 2026_8:30am"
    # Cleanup đơn giản: giữ tối đa 50 entries gần nhất
    alerts = state.get("alerted_events", [])
    if len(alerts) > 50:
        state["alerted_events"] = alerts[-50:]

    return state


# ============================================================
# GỬI TELEGRAM
# ============================================================
def send_telegram(message: str) -> bool:
    if not TELEGRAM_TOKEN or not CHAT_ID:
        log.error("TELEGRAM_TOKEN hoặc CHAT_ID chưa được set!")
        return False
    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, data=payload, timeout=15)
        resp.raise_for_status()
        log.info("✅ Telegram OK: %s", message[:70].replace("\n", " "))
        return True
    except requests.RequestException as e:
        log.error("❌ Telegram lỗi: %s", e)
        return False


# ============================================================
# PARSE THỜI GIAN FOREXFACTORY
# ============================================================
_NON_TIME_VALUES = {"all day", "tentative", "data", "tba", "n/a", ""}
_DATE_FORMATS    = ["%a %b %d %Y", "%b %d, %Y", "%m/%d/%Y", "%Y-%m-%d"]
_TIME_FORMATS    = ["%I:%M%p", "%H:%M", "%I%p"]


def _parse_date_only(date_s: str):
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(date_s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def parse_ff_datetime(date_s: str, time_s: str, impact: str = "High"):
    """
    Chuyển (date_s, time_s) từ ForexFactory RSS (ET) → datetime aware VN.
    • High    : parse date + time → localize ET → convert VN
    • Holiday : parse date only → 00:00 ET → convert VN (luôn có dt_local)
    • Trả None chỉ khi không parse được date_s
    """
    if not date_s:
        return None

    time_s       = (time_s or "").strip()
    is_non_time  = time_s.lower() in _NON_TIME_VALUES

    # Holiday hoặc không có giờ: gán 00:00 ET của ngày đó
    if impact == "Holiday" or is_non_time:
        parsed_date = _parse_date_only(date_s)
        if parsed_date is None:
            return None
        dt_et = ET_ZONE.localize(
            datetime(parsed_date.year, parsed_date.month, parsed_date.day, 0, 0, 0)
        )
        return dt_et.astimezone(TIMEZONE)

    # High: thử các tổ hợp format
    for dfmt in _DATE_FORMATS:
        for tfmt in _TIME_FORMATS:
            try:
                dt_naive = datetime.strptime(f"{date_s.strip()} {time_s}", f"{dfmt} {tfmt}")
                return ET_ZONE.localize(dt_naive).astimezone(TIMEZONE)
            except ValueError:
                continue

    log.warning("Không parse được: date='%s' time='%s' impact=%s", date_s, time_s, impact)
    return None


# ============================================================
# LẤY & PARSE RSS FOREXFACTORY
# ============================================================
def fetch_events() -> list:
    """
    Lấy RSS ForexFactory, trả về list event High + Holiday trong tuần.
    Mỗi phần tử: { id, title, country, date_s, time_s, impact, dt_local }
    dt_local luôn có giá trị (Holiday dùng 00:00 ET).
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; ForexNewsBot/3.0; +https://github.com)"
        )
    }
    try:
        resp = requests.get(FF_RSS_URL, headers=headers, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.error("❌ Fetch RSS lỗi: %s", e)
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        log.error("❌ Parse XML lỗi: %s", e)
        return []

    channel = root.find("channel")
    if channel is None:
        return []

    events = []
    for item in channel.findall("item"):
        impact_el = item.find("impact")
        if impact_el is None or not impact_el.text:
            continue
        impact = impact_el.text.strip()
        if impact not in ("High", "Holiday"):
            continue

        def _text(tag):
            el = item.find(tag)
            return el.text.strip() if el is not None and el.text else ""

        title    = _text("title")   or "N/A"
        country  = _text("country") or "??"
        date_s   = _text("date")
        time_s   = _text("time")

        dt_local = parse_ff_datetime(date_s, time_s, impact)
        if dt_local is None:
            log.debug("Skip (không parse date): [%s] %s %s", impact, country, title)
            continue

        event_id = f"{country}_{title}_{date_s}_{time_s}"
        events.append({
            "id":       event_id,
            "title":    title,
            "country":  country,
            "date_s":   date_s,
            "time_s":   time_s,
            "impact":   impact,
            "dt_local": dt_local,
        })

    log.info("📡 RSS: %d sự kiện (High + Holiday) trong tuần.", len(events))
    return events


# ============================================================
# BỘ LỌC SỰ KIỆN
# ============================================================
def events_on_date(events: list, target_date: date) -> list:
    result = [ev for ev in events if ev["dt_local"].date() == target_date]
    result.sort(key=lambda x: x["dt_local"])
    return result


def events_after(events: list, cutoff_dt: datetime) -> list:
    """
    Sự kiện hôm nay chưa diễn ra tính từ cutoff_dt.
    Holiday luôn giữ lại (ảnh hưởng cả ngày).
    """
    today  = cutoff_dt.date()
    result = []
    for ev in events:
        if ev["dt_local"].date() != today:
            continue
        if ev["impact"] == "Holiday" or ev["dt_local"] >= cutoff_dt:
            result.append(ev)
    result.sort(key=lambda x: x["dt_local"])
    return result


# ============================================================
# XÂY DỰNG NỘI DUNG BÁO CÁO
# ============================================================
def format_event_line(ev: dict) -> str:
    if ev["impact"] == "Holiday":
        return f"🏦 <b>Nghỉ lễ</b>: {ev['country']} — {ev['title']}"
    t = ev["dt_local"].strftime("%H:%M")
    return f"🔴 <b>{t}</b>  [{ev['country']}]  {ev['title']}"


def build_report(title_header: str, date_label: str, ev_list: list, empty_msg: str) -> str:
    lines = [f"<b>{title_header}</b>", f"📅 {date_label}", ""]

    if not ev_list:
        lines.append(empty_msg)
    else:
        high_evs    = [e for e in ev_list if e["impact"] == "High"]
        holiday_evs = [e for e in ev_list if e["impact"] == "Holiday"]

        if holiday_evs:
            lines.append("── Ngân hàng nghỉ lễ ──")
            for ev in holiday_evs:
                lines.append(format_event_line(ev))
            lines.append("")

        if high_evs:
            lines.append("── Tin tức đỏ ──")
            for ev in high_evs:
                lines.append(format_event_line(ev))
            lines.append("")
            lines.append(f"⚠️ Tổng <b>{len(high_evs)}</b> tin đỏ — Chú ý quản lý vị thế FTMO!")
        elif holiday_evs:
            lines.append("✅ Không có tin đỏ, chỉ có ngân hàng nghỉ lễ.")

    return "\n".join(lines)


# ============================================================
# LOGIC CHÍNH  (one-shot)
# ============================================================
def run(state: dict) -> dict:
    """
    Hàm chính: nhận state hiện tại, xử lý logic, trả về state mới.
    Được gọi 1 lần mỗi khi GitHub Actions trigger.
    """
    now    = datetime.now(TIMEZONE)
    today  = now.date()
    dow    = now.isoweekday()   # 1=Mon … 7=Sun

    log.info("▶ Run lúc %s (Thứ %d)", now.strftime("%Y-%m-%d %H:%M:%S %Z"), dow)

    # ── Cuối tuần: bỏ qua ────────────────────────────────────
    if dow >= 6:
        log.info("😴 Cuối tuần — không xử lý.")
        return state

    # ── Lấy dữ liệu RSS ──────────────────────────────────────
    events = fetch_events()
    if not events:
        log.warning("Không lấy được dữ liệu RSS. Bỏ qua lần này.")
        return state

    date_label        = f"{today.strftime('%d/%m/%Y')} — Thứ {dow}"
    alerted_set       = set(state.get("alerted_events", []))
    sent_checkpoints  = set(state.get("sent_checkpoints", []))

    # ── MỐC 1: 05:00 Sáng ────────────────────────────────────
    # Workflow chạy mỗi 10 phút → có thể trigger lúc 05:00 hoặc 05:10
    # Dùng cửa sổ [H:00, H:09] để không bỏ sót
    def in_window(target_hour: int) -> bool:
        return now.hour == target_hour and now.minute <= CHECKPOINT_WINDOW

    if in_window(MORNING_HOUR):
        key = f"{today}_0500"
        if key not in sent_checkpoints:
            ev_day = events_on_date(events, today)
            msg    = build_report(
                title_header = "🗓 TỔNG HỢP TIN TỨC ĐẦU NGÀY",
                date_label   = date_label,
                ev_list      = ev_day,
                empty_msg    = "✅ Hôm nay <b>không có tin tức nào cần lưu ý</b>. Giao dịch bình thường.",
            )
            if send_telegram(msg):
                sent_checkpoints.add(key)
                log.info("📬 Đã gửi báo cáo sáng: %s", key)

    # ── MỐC 2: 12:00 Trưa ────────────────────────────────────
    elif in_window(NOON_HOUR):
        key = f"{today}_1200"
        if key not in sent_checkpoints:
            ev_rem = events_after(events, now)
            msg    = build_report(
                title_header = "☀️ CẬP NHẬT TRƯA — TIN TỨC CÒN LẠI",
                date_label   = date_label,
                ev_list      = ev_rem,
                empty_msg    = "✅ Không còn tin tức nào trong buổi chiều/tối hôm nay.",
            )
            if send_telegram(msg):
                sent_checkpoints.add(key)
                log.info("📬 Đã gửi báo cáo trưa: %s", key)

    # ── MỐC 3: 17:00 Chiều ───────────────────────────────────
    elif in_window(EVENING_HOUR):
        key = f"{today}_1700"
        if key not in sent_checkpoints:
            ev_rem = events_after(events, now)
            msg    = build_report(
                title_header = "🌆 CẬP NHẬT CHIỀU — PHIÊN MỸ SẮP MỞ",
                date_label   = date_label,
                ev_list      = ev_rem,
                empty_msg    = "✅ Không có tin đỏ nào trong phiên Mỹ tối nay.",
            )
            if send_telegram(msg):
                sent_checkpoints.add(key)
                log.info("📬 Đã gửi báo cáo chiều: %s", key)

    # ── MỐC 4: Cảnh báo khẩn T-10 phút ──────────────────────
    # Luôn chạy bất kể giờ nào (không dùng elif)
    for ev in events:
        if ev["impact"] != "High":
            continue
        if ev["id"] in alerted_set:
            continue

        diff_min = (ev["dt_local"] - now).total_seconds() / 60

        # Cửa sổ cảnh báo: [ALERT_BEFORE_MIN, ALERT_WINDOW_MIN]
        # = [10, 12] phút → bắt được dù job chạy hơi trễ
        if ALERT_BEFORE_MIN <= diff_min <= ALERT_WINDOW_MIN:
            minutes_left = int(diff_min)
            msg = (
                f"🚨 <b>CẢNH BÁO KHẨN — TIN ĐỎ SẮP DIỄN RA!</b>\n\n"
                f"⏰ Giờ công bố : <b>{ev['dt_local'].strftime('%H:%M')} (GMT+7)</b>\n"
                f"🌍 Quốc gia    : <b>{ev['country']}</b>\n"
                f"📰 Tin tức     : <b>{ev['title']}</b>\n"
                f"⏳ Còn khoảng : <b>{minutes_left} phút</b>\n\n"
                f"👉 Kiểm tra & quản lý vị thế FTMO ngay!"
            )
            if send_telegram(msg):
                alerted_set.add(ev["id"])
                log.info(
                    "🔔 Đã alert T-10: %s @ %s VN",
                    ev["title"], ev["dt_local"].strftime("%H:%M"),
                )

    # ── Cập nhật state ────────────────────────────────────────
    state["alerted_events"]   = list(alerted_set)
    state["sent_checkpoints"] = list(sent_checkpoints)
    return state


# ============================================================
# ENTRY POINT
# ============================================================
def main():
    if not TELEGRAM_TOKEN:
        log.error("❌ TELEGRAM_TOKEN chưa set. Thoát.")
        sys.exit(1)
    if not CHAT_ID:
        log.error("❌ CHAT_ID chưa set. Thoát.")
        sys.exit(1)

    # 1. Load state
    state = load_state()

    # 2. Cleanup state cũ
    now   = datetime.now(TIMEZONE)
    state = cleanup_old_state(state, now.date())

    # 3. Chạy logic chính
    state = run(state)

    # 4. Lưu state mới
    save_state(state)

    log.info("✅ Bot hoàn thành.")


if __name__ == "__main__":
    main()
