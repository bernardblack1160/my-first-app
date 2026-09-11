from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI()

# مسیر دایرکتوری فرانت‌اند (به صورت نسبی)
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")

# سرو کردن فایل‌های استاتیک
app.mount("/static", StaticFiles(directory=os.path.join(frontend_dir, "src")), name="static")
app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="assets")

# مسیرهای اصلی اپلیکیشن
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/sw.js")
async def serve_sw():
    return FileResponse(os.path.join(frontend_dir, "sw.js"))

@app.get("/manifest.webmanifest")
async def serve_manifest():
    return FileResponse(os.path.join(frontend_dir, "manifest.webmanifest"))

@app.get("/worker.js")
async def serve_worker():
    return FileResponse(os.path.join(frontend_dir, "worker.js"))
