import requests
import base64
import re
import random
from datetime import datetime
import os

# رنگ‌ها برای ترمینال
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

# منابع ساب‌لینک
SOURCES = [
    "https://sub.shadowproxy66.workers.dev/sub/fed93ccf-b024-4494-98e5-1d2d2325d872",
    "https://sub.shadowproxy66.workers.dev/sub/be80a76c-6044-417c-9bff-e587f9380d05",
    "https://sub.shadowproxy66.workers.dev/sub/99066519-727d-44d0-b65a-6034f21bf3a2"
]

# تابع لاگ رنگی
def log(message, type="info"):
    if type == "success":
        print(f"{GREEN}[✓] {message}{RESET}")
    elif type == "error":
        print(f"{RED}[✗] {message}{RESET}")
    elif type == "wait":
        print(f"{YELLOW}[~] {message}{RESET}")
    else:
        print(f"[i] {message}")

# تابع دریافت و دیکد کانفیگ‌ها از یک ساب‌لینک
def fetch_configs(url):
    try:
        log(f"دریافت از: {url}", "wait")
        response = requests.get(url, timeout=30)
        
        if response.status_code != 200:
            log(f"خطا در دریافت {url} - کد {response.status_code}", "error")
            return []
        
        content = response.text.strip()
        
        # بررسی اگر base64 باشه
        try:
            decoded = base64.b64decode(content).decode('utf-8')
            configs = decoded.splitlines()
        except:
            # اگر base64 نباشه مستقیم خطوط
            configs = content.splitlines()
        
        log(f"دریافت {len(configs)} کانفیگ از این منبع", "success")
        return configs
        
    except Exception as e:
        log(f"خطا در {url}: {str(e)}", "error")
        return []

# تابع پاک کردن متن بعد از # و ایموجی‌ها
def clean_config(line):
    # حذف هر چیزی که بعد از # اومده (شامل # خودش)
    line = re.sub(r'#.*$', '', line)
    # حذف ایموجی‌ها (اختیاری - اگه خواستی پاک بشن)
    # ایموجی‌ها معمولاً در UTF-8 باقی می‌مونن، ولی خط بالا # رو حذف می‌کنه
    return line.strip()

# تابع اصلی
def main():
    log("شروع به روزرسانی ساب‌لینک", "wait")
    
    all_configs = []
    
    # مرحله 1: دریافت از همه منابع
    for url in SOURCES:
        configs = fetch_configs(url)
        if configs:
            all_configs.extend(configs)
    
    if not all_configs:
        log("هیچ کانفیگی دریافت نشد!", "error")
        return
    
    log(f"مجموع کانفیگ‌های خام: {len(all_configs)}", "success")
    
    # مرحله 2: تمیز کردن کانفیگ‌ها (حذف # و بعدش)
    cleaned = []
    for conf in all_configs:
        conf = clean_config(conf)
        if conf and len(conf) > 10:  # فیلتر خطوط خالی یا خیلی کوتاه
            cleaned.append(conf)
    
    log(f"بعد از پاکسازی: {len(cleaned)} کانفیگ", "success")
    
    # مرحله 3: انتخاب 600 تا رندوم
    if len(cleaned) > 600:
        selected = random.sample(cleaned, 600)
    else:
        selected = cleaned[:]
        log(f"تعداد کانفیگ کمتر از 600 بود، همه {len(selected)} تا استفاده شد", "wait")
    
    # مرحله 4: اضافه کردن تگ با شماره منظم
    final_configs = []
    for idx, conf in enumerate(selected, start=1):
        # اضافه کردن #🔥 Channel : @nitruStore به همراه شماره
        tag = f"#🔥{idx} Channel : @nitruStore"
        final_configs.append(f"{conf}{tag}")
    
    # مرحله 5: اضافه کردن کانفیگ مخصوص زمان آخرین آپدیت (همیشه در خط اول)
    now = datetime.now()
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # یک کانفیگ کامنت‌گونه که در کلاینت‌ها نمایش داده بشه
    update_config = f"vmess://#{time_str}?remarks=LastUpdate-{time_str}"
    # یا بهتر: یک لینک بی اثر که فقط توضیح بده
    update_remark = f"# Last Update: {time_str} - کانفیگ‌ها تازه‌ان"
    
    # قرار دادن در صدر
    final_configs.insert(0, update_remark)
    final_configs.insert(0, update_config)
    
    # مرحله 6: ذخیره در فایل sub.txt
    with open("sub.txt", "w", encoding="utf-8") as f:
        for conf in final_configs:
            f.write(conf + "\n")
    
    log(f"✅ فایل sub.txt با {len(final_configs)} خط ذخیره شد", "success")
    log(f"آخرین بروزرسانی: {time_str}", "success")

if __name__ == "__main__":
    main()
