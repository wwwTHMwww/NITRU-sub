#!/usr/bin/env python3
import requests
import base64
import re
import random
import json
from datetime import datetime
import time
import os

try:
    from config import *
except ImportError:
    print("❌ config.py پیدا نشد!")
    exit(1)

try:
    from telegram import send_telegram_message, send_file_to_telegram
except ImportError:
    def send_telegram_message(msg): return False
    def send_file_to_telegram(file, cap): return False

# رنگ‌ها برای ترمینال
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"

def log(msg, t="info"):
    if t == "success":
        print(f"{GREEN}✅ {msg}{RESET}")
    elif t == "error":
        print(f"{RED}❌ {msg}{RESET}")
    elif t == "wait":
        print(f"{YELLOW}⏳ {msg}{RESET}")
    elif t == "info":
        print(f"{BLUE}📡 {msg}{RESET}")
    elif t == "channel":
        print(f"{CYAN}🏷️ {msg}{RESET}")

def fetch_source(url, retry=0):
    try:
        log(f"دریافت از منبع...", "wait")
        r = requests.get(url, timeout=TIMEOUT)
        if r.status_code != 200:
            raise Exception(f"HTTP {r.status_code}")
        try:
            decoded = base64.b64decode(r.text).decode('utf-8')
            configs = decoded.splitlines()
        except:
            configs = r.text.splitlines()
        configs = [c.strip() for c in configs if c.strip() and len(c) > 20]
        log(f"✅ دریافت {len(configs)} کانفیگ", "success")
        return configs
    except Exception as e:
        if retry < MAX_RETRIES:
            log(f"تلاش مجدد ({retry + 1}/{MAX_RETRIES})...", "wait")
            time.sleep(2)
            return fetch_source(url, retry + 1)
        log(f"خطا: {str(e)}", "error")
        return []

def clean_config(c):
    """حذف تگ‌های قدیمی"""
    return re.sub(r'#.*$', '', c).strip()

def rename_config(c, idx):
    """تغییر نام به فرمت: کانفیگ#شماره Channel : @nitruStore"""
    clean = clean_config(c)
    return f"{clean}#{idx} {FINAL_TAG}"

def create_info_config(total_configs):
    """ساخت کانفیگ اطلاعات با فرمت NITRU"""
    now = datetime.now()
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # محاسبه دقیقه از آخرین آپدیت
    minute_of_day = now.hour * 60 + now.minute
    
    info_config = {
        "v": "2",
        "ps": f"📊 NITRU | Last Update: {time_str} | Total: {total_configs} Configs | {CHANNEL_TAG}",
        "add": "185.159.157.229",
        "port": "443",
        "id": "nitru-info-display",
        "aid": "0",
        "scy": "auto",
        "net": "ws",
        "type": "none",
        "host": "info.nitru.ir",
        "path": "/info",
        "tls": "tls"
    }
    
    vmess_json = json.dumps(info_config)
    vmess_b64 = base64.b64encode(vmess_json.encode()).decode()
    return f"vmess://{vmess_b64}"

def main():
    start_time = datetime.now()
    
    log("=" * 50, "info")
    log("🚀 شروع بروزرسانی NITRU Sub Link", "info")
    log(f"🏷️ کانال: {CHANNEL_TAG}", "channel")
    log(f"📊 تعداد هدف: {TOTAL_CONFIGS} کانفیگ", "info")
    log("=" * 50, "info")
    
    log(f"تعداد منابع: {len(SOURCES)}", "info")
    
    source_stats = []
    all_configs = []
    
    for i, url in enumerate(SOURCES, 1):
        log(f"\n📡 منبع {i}:", "info")
        configs = fetch_source(url)
        source_stats.append(f"📡 منبع {i}: {len(configs)} کانفیگ")
        all_configs.extend(configs)
    
    if not all_configs:
        log("❌ هیچ کانفیگی دریافت نشد!", "error")
        send_telegram_message("❌ <b>خطا در بروزرسانی NITRU</b>\n\nهیچ کانفیگی از منابع دریافت نشد!")
        return False
    
    log(f"\n📊 مجموع کانفیگ‌های خام: {len(all_configs)}", "success")
    
    # حذف تکراری
    unique = []
    seen = set()
    for c in all_configs:
        key = re.sub(r'#.*$', '', c)
        if key not in seen:
            seen.add(key)
            unique.append(c)
    
    log(f"📊 بعد از حذف تکراری: {len(unique)} کانفیگ", "success")
    
    # انتخاب تصادفی
    if len(unique) > TOTAL_CONFIGS:
        selected = random.sample(unique, TOTAL_CONFIGS)
        log(f"🎲 انتخاب {TOTAL_CONFIGS} کانفیگ به صورت تصادفی", "success")
    else:
        selected = unique
        log(f"📊 تعداد کمتر از {TOTAL_CONFIGS}، همه {len(selected)} تا استفاده شد", "wait")
    
    # تغییر نام به فرمت NITRU
    log(f"\n🏷️ در حال تغییر نام کانفیگ‌ها به فرمت NITRU...", "wait")
    renamed = []
    for i, c in enumerate(selected, 1):
        new_name = rename_config(c, i)
        renamed.append(new_name)
    
    log(f"✅ نام {len(renamed)} کانفیگ با موفقیت تغییر کرد", "success")
    
    # کانفیگ اطلاعات
    info_config = create_info_config(len(renamed))
    final = [info_config] + renamed
    
    # ذخیره در فایل
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final))
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    log("\n" + "=" * 50, "success")
    log("✅ عملیات با موفقیت انجام شد!", "success")
    log(f"📁 فایل {OUTPUT_FILE} ذخیره شد", "success")
    log(f"📊 آمار نهایی:", "info")
    log(f"   • کانفیگ اطلاعات: 1 عدد", "info")
    log(f"   • کانفیگ NITRU: {len(renamed)} عدد", "info")
    log(f"   • مجموع کل: {len(final)} عدد", "info")
    log(f"⏱️ زمان اجرا: {duration:.2f} ثانیه", "info")
    log("=" * 50, "success")
    
    # نمونه از خروجی
    if len(final) > 1:
        log(f"\n📝 نمونه از کانفیگ نهایی:", "info")
        sample = final[1][:100] + "..." if len(final[1]) > 100 else final[1]
        log(f"   {sample}", "info")
    
    # ارسال به تلگرام
    tg_message = f"""
<b>🛡️ NITRU Sub Link - گزارش بروزرسانی</b>

⏰ <b>زمان:</b> {end_time.strftime('%Y-%m-%d %H:%M:%S')}
⚡ <b>مدت اجرا:</b> {duration:.2f} ثانیه
🏷️ <b>کانال:</b> {CHANNEL_TAG}

<b>📥 دریافت از منابع:</b>
{chr(10).join(source_stats)}

<b>📊 آمار نهایی:</b>
• کانفیگ خام: {len(all_configs)}
• بعد از حذف تکراری: {len(unique)}
• کانفیگ نهایی NITRU: {len(renamed)}
• کانفیگ اطلاعات: 1

<b>📁 لینک ساب‌لینک:</b>
<code>https://raw.githubusercontent.com/{os.environ.get('GITHUB_REPOSITORY', 'USER/NITRU-Sub')}/main/sub.txt</code>

✅ <b>وضعیت:</b> موفق | <b>کانال:</b> {CHANNEL_TAG}
    """
    
    send_telegram_message(tg_message)
    send_file_to_telegram(OUTPUT_FILE, f"📁 NITRU Sub - {end_time.strftime('%Y-%m-%d %H:%M:%S')} | {CHANNEL_TAG}")
    
    return True

if __name__ == "__main__":
    exit(0 if main() else 1)
