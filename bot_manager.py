import requests
import json
import os
import re
from datetime import datetime

# تنظیمات
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "")
CONFIG_FILE = "config.py"

# آدرس‌های API گیت‌هاب
GITHUB_API = f"https://api.github.com/repos/{REPO_NAME}/contents/{CONFIG_FILE}"

def is_admin(chat_id):
    """چک کردن ادمین بودن"""
    return str(chat_id) == str(CHAT_ID)

def get_current_config():
    """دریافت فایل config.py فعلی از گیت‌هاب"""
    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        r = requests.get(GITHUB_API, headers=headers)
        if r.status_code == 200:
            content = r.json()
            import base64
            config_content = base64.b64decode(content['content']).decode('utf-8')
            return config_content, content['sha']
        return None, None
    except Exception as e:
        print(f"خطا: {e}")
        return None, None

def update_config_on_github(new_content, old_sha):
    """آپدیت فایل config.py روی گیت‌هاب"""
    try:
        import base64
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        data = {
            "message": f"Update sources via Telegram bot - {datetime.now()}",
            "content": base64.b64encode(new_content.encode()).decode(),
            "sha": old_sha,
            "branch": "main"
        }
        
        r = requests.put(GITHUB_API, headers=headers, json=data)
        return r.status_code == 200
    except Exception as e:
        print(f"خطا: {e}")
        return False

def extract_sources_from_config(content):
    """استخراج لیست منابع از فایل config"""
    import re
    pattern = r'SOURCES\s*=\s*\[(.*?)\]'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        sources_text = match.group(1)
        sources = re.findall(r'"([^"]+)"', sources_text)
        return sources
    return []

def update_sources_in_config(content, new_sources):
    """آپدیت لیست منابع در فایل config"""
    import re
    sources_str = ",\n    ".join([f'"{s}"' for s in new_sources])
    new_sources_block = f"SOURCES = [\n    {sources_str}\n]"
    
    pattern = r'SOURCES\s*=\s*\[.*?\]'
    new_content = re.sub(pattern, new_sources_block, content, flags=re.DOTALL)
    return new_content

def send_message(chat_id, text, reply_to=None):
    """ارسال پیام به تلگرام"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def send_list_sources(chat_id):
    """نمایش لیست منابع"""
    content, _ = get_current_config()
    if not content:
        send_message(chat_id, "❌ خطا در دریافت فایل تنظیمات!")
        return
    
    sources = extract_sources_from_config(content)
    
    if not sources:
        send_message(chat_id, "📭 هیچ منبعی یافت نشد!")
        return
    
    msg = "<b>📋 لیست منابع ساب‌لینک:</b>\n\n"
    for i, src in enumerate(sources, 1):
        short_src = src[:60] + "..." if len(src) > 60 else src
        msg += f"{i}. <code>{short_src}</code>\n"
    
    msg += f"\n📊 <b>تعداد کل منابع:</b> {len(sources)}"
    send_message(chat_id, msg)

def add_new_source(chat_id, new_url):
    """اضافه کردن منبع جدید"""
    # اعتبارسنجی URL
    if not new_url.startswith("http"):
        send_message(chat_id, "❌ لینک نامعتبر! لطفاً با http:// یا https:// شروع کنید.")
        return
    
    content, sha = get_current_config()
    if not content:
        send_message(chat_id, "❌ خطا در دریافت فایل تنظیمات!")
        return
    
    sources = extract_sources_from_config(content)
    
    if new_url in sources:
        send_message(chat_id, "⚠️ این منبع قبلاً اضافه شده است!")
        return
    
    sources.append(new_url)
    new_content = update_sources_in_config(content, sources)
    
    if update_config_on_github(new_content, sha):
        send_message(chat_id, f"✅ منبع جدید با موفقیت اضافه شد!\n\n<code>{new_url}</code>")
        # اجرای مجدد اسکریپت آپدیت
        trigger_update_workflow()
    else:
        send_message(chat_id, "❌ خطا در ذخیره تغییرات روی گیت‌هاب!")

def remove_source(chat_id, index):
    """حذف منبع با شماره"""
    content, sha = get_current_config()
    if not content:
        send_message(chat_id, "❌ خطا در دریافت فایل تنظیمات!")
        return
    
    sources = extract_sources_from_config(content)
    
    try:
        idx = int(index) - 1
        if idx < 0 or idx >= len(sources):
            send_message(chat_id, f"❌ شماره نامعتبر! لطفاً عددی بین 1 تا {len(sources)} وارد کنید.")
            return
        
        removed = sources.pop(idx)
        new_content = update_sources_in_config(content, sources)
        
        if update_config_on_github(new_content, sha):
            send_message(chat_id, f"✅ منبع با موفقیت حذف شد!\n\n<code>{removed}</code>")
            trigger_update_workflow()
        else:
            send_message(chat_id, "❌ خطا در ذخیره تغییرات روی گیت‌هاب!")
    except ValueError:
        send_message(chat_id, "❌ لطفاً یک عدد معتبر وارد کنید!")

def trigger_update_workflow():
    """اجرای مجدد workflow آپدیت"""
    url = f"https://api.github.com/repos/{REPO_NAME}/actions/workflows/update.yml/dispatches"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "ref": "main"
    }
    
    try:
        requests.post(url, headers=headers, json=data, timeout=10)
        print("✅ Workflow اجرا شد")
    except:
        print("❌ خطا در اجرای workflow")

def handle_message(update):
    """پردازش پیام‌های دریافتی"""
    if "message" not in update:
        return
    
    message = update["message"]
    chat_id = message["chat"]["id"]
    
    # چک کردن ادمین
    if not is_admin(chat_id):
        send_message(chat_id, "⛔ شما دسترسی به این ربات ندارید!")
        return
    
    text = message.get("text", "")
    reply_id = message.get("message_id")
    
    # دستورات
    if text == "/start":
        welcome = """
<b>🤖 ربات مدیریت NITRU Sub Link</b>

دستورات موجود:

🔹 <b>/sources</b> - نمایش لیست منابع
🔹 <b>/add [لینک]</b> - اضافه کردن منبع جدید
🔹 <b>/remove [شماره]</b> - حذف منبع با شماره
🔹 <b>/update</b> - اجرای دستی بروزرسانی
🔹 <b>/help</b> - راهنما

مثال:
<code>/add https://example.com/sub</code>
<code>/remove 3</code>
"""
        send_message(chat_id, welcome)
    
    elif text == "/sources" or text == "/list":
        send_list_sources(chat_id)
    
    elif text.startswith("/add "):
        new_url = text[5:].strip()
        if new_url:
            add_new_source(chat_id, new_url)
        else:
            send_message(chat_id, "❌ لطفاً لینک معتبر وارد کنید!\nمثال: <code>/add https://example.com/sub</code>")
    
    elif text.startswith("/remove "):
        index = text[8:].strip()
        if index:
            remove_source(chat_id, index)
        else:
            send_message(chat_id, "❌ لطفاً شماره منبع را وارد کنید!\nمثال: <code>/remove 3</code>")
    
    elif text == "/update":
        send_message(chat_id, "🔄 در حال اجرای بروزرسانی...")
        trigger_update_workflow()
        send_message(chat_id, "✅ بروزرسانی با موفقیت آغاز شد!")
    
    elif text == "/help":
        help_text = """
<b>📖 راهنمای دستورات NITRU Bot</b>

▪️ <b>/sources</b> - نمایش لیست همه منابع با شماره
▪️ <b>/add [لینک]</b> - اضافه کردن منبع جدید
▪️ <b>/remove [شماره]</b> - حذف منبع (شماره رو از /sources ببین)
▪️ <b>/update</b> - اجرای دستی بروزرسانی ساب‌لینک
▪️ <b>/help</b> - نمایش این راهنما
▪️ <b>/start</b> - خوش‌آمدگویی

<b>⚠️ نکته:</b>
بعد از هر تغییر، ساب‌لینک خودکار آپدیت میشه
"""
        send_message(chat_id, help_text)
    
    else:
        send_message(chat_id, "❌ دستور نامعتبر!\nبرای مشاهده راهنما /help را وارد کنید.")

def main():
    """اجرای ربات (Webhook mode for GitHub)"""
    from flask import Flask, request
    
    app = Flask(__name__)
    
    @app.route(f"/{TOKEN}", methods=["POST"])
    def webhook():
        update = request.get_json()
        if update:
            handle_message(update)
        return "ok", 200
    
    @app.route("/", methods=["GET"])
    def home():
        return "NITRU Bot is running!", 200
    
    return app

if __name__ == "__main__":
    app = main()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
