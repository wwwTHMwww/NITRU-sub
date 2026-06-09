import requests
import os

def send_telegram_message(message):
    """ارسال پیام به تلگرام"""
    TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
    
    if not TOKEN or not CHAT_ID:
        print("⚠️ تلگرام تنظیم نشده است!")
        return False
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("✅ پیام به تلگرام ارسال شد")
            return True
        else:
            print(f"❌ خطا در ارسال پیام: {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ خطا: {str(e)}")
        return False

def send_file_to_telegram(file_path, caption=""):
    """ارسال فایل به تلگرام"""
    TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
    
    if not TOKEN or not CHAT_ID:
        return False
    
    if not os.path.exists(file_path):
        return False
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
    
    try:
        with open(file_path, "rb") as f:
            files = {"document": f}
            data = {"chat_id": CHAT_ID, "caption": caption}
            r = requests.post(url, files=files, data=data, timeout=30)
            return r.status_code == 200
    except:
        return False
