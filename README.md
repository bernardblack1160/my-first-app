# lila web frontend

رابط وبی ماژولار و قابل نصب به شکل PWA است. فایل‌های HTML، CSS و JavaScript بدون وابستگی build سنگین در `src/` قرار دارند و API را از `/api` دریافت می‌کنند.

برای اجرای مستقل frontend:

```bash
python -m http.server 8080
```

در این حالت API باید روی پورت 8000 در دسترس باشد و `API_CORS_ORIGINS=http://localhost:8080` تنظیم شود. برای اجرای یکپارچه، از ریشهٔ پروژه Docker Compose را اجرا کنید تا FastAPI فایل‌های frontend را نیز سرو کند.

## پیش‌نمایش ظاهر

`preview.html` یک پیش‌نمایش کاملاً محلی با دادهٔ ساختگی است؛ به PostgreSQL یا Supabase وصل نمی‌شود و هیچ داده‌ای را ذخیره نمی‌کند. تصویر بررسی‌شدهٔ `docs/mobile-preview-390.png` در صورت درخواست می‌تواند با snapshot دادهٔ فعلی ساخته شود، اما دادهٔ واقعی هرگز داخل fixture یا کد release قرار نمی‌گیرد.

سرویس‌ورکر اصلی `worker.js` است؛ `sw.js` فقط wrapper سازگاری برای نسخه‌های قدیمی است. هر دو فایل باید در ریشهٔ frontend موجود باشند.

برای پیش‌نمایش سریع:

```bash
python -m http.server 8080
```

سپس `http://localhost:8080/preview.html` را باز کنید.
