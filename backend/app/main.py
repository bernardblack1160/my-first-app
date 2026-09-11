import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# مسیر فایل‌های استاتیک و ایندکس
# چون فایل‌ها در ریشه پروژه هستند (طبق خروجی قبلی)، مسیر را اینجا تنظیم می‌کنیم
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# مسیرهای API
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

# سرو کردن فایل‌های استاتیک (عکس‌ها و...)
if os.path.exists(os.path.join(FRONTEND_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

# سرو کردن ایندکس
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
