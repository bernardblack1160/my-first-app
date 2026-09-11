import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# مسیر فایل‌ها را به صورت دستی و دقیق‌تر ست می‌کنیم
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# مسیرهای API
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

# سرو کردن فایل‌های استاتیک
app.mount("/src", StaticFiles(directory=os.path.join(FRONTEND_DIR, "src")), name="src")
app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

# سرو کردن ایندکس
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
