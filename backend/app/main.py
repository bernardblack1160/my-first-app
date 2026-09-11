import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# یافتن مسیر مطلق دایرکتوری ریشه پروژه
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
frontend_dir = os.path.join(base_dir, "frontend")

# سرو کردن فایل‌های استاتیک
# چک می‌کنیم دایرکتوری وجود دارد تا کرش نکند
if os.path.exists(os.path.join(frontend_dir, "src")):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_dir, "src")), name="static")

if os.path.exists(os.path.join(frontend_dir, "assets")):
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
