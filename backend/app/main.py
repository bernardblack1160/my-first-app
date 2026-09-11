import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# مسیر فایل‌های استاتیک و ایندکس
# اینجا داریم به صورت مستقیم می‌گوییم فایل‌ها در پوشه frontend در ریشه پروژه هستند
BASE_DIR = os.getcwd() 
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# مسیرهای API
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

# سرو کردن فایل‌های استاتیک (مثل عکس‌ها و فایل‌های js/css)
app.mount("/src", StaticFiles(directory=os.path.join(FRONTEND_DIR, "src")), name="src")
app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

# سرو کردن ایندکس
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
