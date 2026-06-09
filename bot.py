import requests
import json
import os
import re
import time
from datetime import datetime

# ==================== تنظیمات ====================
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "")
CONFIG_FILE = "config.py"

if not TOKEN:
    print("❌ TELEGRAM_TOKEN تنظیم نشده!")
    exit(1)

# آدرس API تلگرام
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

# ==================== توابع کمکی ====================
def send_message(chat_id, text, reply_to=None):
    """ارسال پیام به تلگرام"""
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"خطا در ارسال پیام: {e}")
        return False

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
        url = f"https://api.github.com/repos/{REPO_NAME}/contents/{CONFIG_FILE}"
        r = requests.get(url, headers=headers)
        
        if r.status_code == 200:
            content = r.json()
            import base64
            config_content = base64.b64decode(content['content']).decode('utf-8')
            return config_content, content['sha']
        return None, None
    except Exception as e:
        print(f"خطا در دریافت config: {e}")
        return None, None

def update_config_on_github(new_content, old_sha):
    """آپدیت فایل config.py روی گیت‌هاب"""
    try:
        import base64
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        url = f"https://api.github.com/repos/{REPO_NAME}/contents/{CONFIG_FILE}"
        data = {
            "message": f"Update sources via Telegram bot - {datetime.now()}",
            "content": base64.b64encode(new_content.encode()).decode(),
            "sha": old_sha,
            "branch": "main"
        }
        
        r = requests.put(url, headers=headers, json=data)
        return r.status_code == 200
    except Exception as e:
        print(f"خطا در آپدیت config: {e}")
        return False

def extract_sources_from_config(content):
    """استخراج لیست منابع از فایل config"""
    pattern = r'SOURCES\s*=\s*\[(.*?)\]'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        sources_text = match.group(1)
        sources = re.findall(r'"([^"]+)"', sources_text)
        return sources
    return []

def update_sources_in_config(content, new_sources):
    """آپدیت لیست منابع در فایل config"""
    sources_str = ",\n    ".join([f'"{s}"' for s in new_sources])
    new_sources_block = f"SOURCES = [\n    {sources_str}\n]"
    
    pattern = r'SOURCES\s*=\s*\[.*?\]'
    new_content = re.sub(pattern, new_sources_block, content, flags=re.DOTALL)
    return new_content

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
        r = requests.post(url, headers=headers, json=data, timeout=10)
        return r.status_code == 204
    except Exception as e:
        print(f"خطا در اجرای workflow: {e}")
        return False

# ==================== دستورات ربات ====================
def handle_start(chat_id):
    msg = """
<b>🤖 ربات مدیریت NITRU Sub Link</b>

به ربات خوش آمدید! این ربات به شما امکان مدیریت ساب‌لینک رو میده.

📋 <b>دستورات موجود:</b>

🔹 <b>/sources</b> - نمایش لیست منابع فعلی
🔹 <b>/add [لینک]</b> - اضافه کردن منبع جدید
🔹 <b>/remove [شماره]</b> - حذف منبع
🔹 <b>/update</b> - اجرای دستی بروزرسانی
🔹 <b>/help</b> - نمایش راهنما

<b>مثال:</b>
<code>/add https://example.com/sub</code>
<code>/remove 3</code>

@nitruStore
"""
    send_message(chat_id, msg)

def handle_sources(chat_id):
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
        short_src = src[:50] + "..." if len(src) > 50 else src
        msg += f"{i}. <code>{short_src}</code>\n"
    
    msg += f"\n📊 <b>تعداد کل منابع:</b> {len(sources)}"
    send_message(chat_id, msg)

def handle_add(chat_id, new_url):
    """اضافه کردن منبع جدید"""
    if not new_url or not new_url.strip():
        send_message(chat_id, "❌ لطفاً لینک معتبر وارد کنید!\nمثال: <code>/add https://example.com/sub</code>")
        return
    
    new_url = new_url.strip()
    
    # اعتبارسنجی URL
    if not (new_url.startswith("http://") or new_url.startswith("https://")):
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
        send_message(chat_id, f"✅ منبع جدید با موفقیت اضافه شد!\n\n<code>{new_url}</code>\n\n🔄 در حال بروزرسانی ساب‌لینک...")
        trigger_update_workflow()
    else:
        send_message(chat_id, "❌ خطا در ذخیره تغییرات روی گیت‌هاب!")

def handle_remove(chat_id, index_str):
    """حذف منبع با شماره"""
    if not index_str or not index_str.strip():
        send_message(chat_id, "❌ لطفاً شماره منبع را وارد کنید!\nمثال: <code>/remove 3</code>")
        return
    
    content, sha = get_current_config()
    if not content:
        send_message(chat_id, "❌ خطا در دریافت فایل تنظیمات!")
        return
    
    sources = extract_sources_from_config(content)
    
    try:
        idx = int(index_str.strip()) - 1
        if idx < 0 or idx >= len(sources):
            send_message(chat_id, f"❌ شماره نامعتبر! لطفاً عددی بین 1 تا {len(sources)} وارد کنید.")
            return
        
        removed = sources.pop(idx)
        new_content = update_sources_in_config(content, sources)
        
        if update_config_on_github(new_content, sha):
            send_message(chat_id, f"✅ منبع با موفقیت حذف شد!\n\n<code>{removed}</code>\n\n🔄 در حال بروزرسانی ساب‌لینک...")
            trigger_update_workflow()
        else:
            send_message(chat_id, "❌ خطا در ذخیره تغییرات روی گیت‌هاب!")
    except ValueError:
        send_message(chat_id, "❌ لطفاً یک عدد معتبر وارد کنید!")

def handle_update(chat_id):
    """اجرای دستی بروزرسانی"""
    send_message(chat_id, "🔄 در حال اجرای بروزرسانی ساب‌لینک...")
    if trigger_update_workflow():
        send_message(chat_id, "✅ بروزرسانی با موفقیت آغاز شد!\nحداکثر 1 دقیقه دیگر ساب‌لینک به‌روز می‌شود.")
    else:
        send_message(chat_id, "❌ خطا در اجرای بروزرسانی!")

def handle_help(chat_id):
    msg = """
<b>📖 راهنمای دستورات NITRU Bot</b>

▪️ <b>/sources</b> - نمایش لیست همه منابع با شماره
▪️ <b>/add [لینک]</b> - اضافه کردن منبع جدید
▪️ <b>/remove [شماره]</b> - حذف منبع (شماره رو از /sources ببین)
▪️ <b>/update</b> - اجرای دستی بروزرسانی ساب‌لینک
▪️ <b>/help</b> - نمایش این راهنما
▪️ <b>/start</b> - صفحه خوش‌آمدگویی

<b>⚠️ نکته مهم:</b>
بعد از هر تغییر، ساب‌لینک خودکار ظرف 1 دقیقه آپدیت میشه.

<b>📥 لینک ساب‌لینک:</b>
<code>https://raw.githubusercontent.com/{REPO_NAME}/main/sub.txt</code>

@nitruStore
"""
    send_message(chat_id, msg)

# ==================== پردازش پیام‌ها ====================
def get_updates(offset=None):
    """دریافت پیام‌های جدید از تلگرام"""
    url = f"{TELEGRAM_API}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    
    try:
        r = requests.get(url, params=params, timeout=35)
        if r.status_code == 200:
            data = r.json()
            if data["ok"]:
                return data["result"]
        return []
    except Exception as e:
        print(f"خطا در دریافت آپدیت: {e}")
        return []

def main():
    """اجرای اصلی ربات با Polling"""
    print("🤖 ربات NITRU شروع به کار کرد...")
    print(f"📡 در حال گوش دادن به دستورات...")
    
    last_update_id = 0
    
    while True:
        try:
            updates = get_updates(last_update_id + 1)
            
            for update in updates:
                if "message" in update:
                    last_update_id = update["update_id"]
                    message = update["message"]
                    chat_id = message["chat"]["id"]
                    text = message.get("text", "")
                    
                    print(f"📩 پیام جدید از {chat_id}: {text}")
                    
                    # چک کردن ادمین
                    if not is_admin(chat_id):
                        send_message(chat_id, "⛔ شما دسترسی به این ربات ندارید!")
                        continue
                    
                    # پردازش دستورات
                    if text == "/start":
                        handle_start(chat_id)
                    elif text == "/sources" or text == "/list":
                        handle_sources(chat_id)
                    elif text.startswith("/add "):
                        new_url = text[5:].strip()
                        handle_add(chat_id, new_url)
                    elif text.startswith("/remove "):
                        index = text[8:].strip()
                        handle_remove(chat_id, index)
                    elif text == "/update":
                        handle_update(chat_id)
                    elif text == "/help":
                        handle_help(chat_id)
                    elif text.startswith("/"):
                        send_message(chat_id, "❌ دستور نامعتبر!\nبرای مشاهده راهنما /help را وارد کنید.")
            
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("\n🛑 ربات متوقف شد.")
            break
        except Exception as e:
            print(f"❌ خطا: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
