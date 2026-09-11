import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# پیدا کردن مسیر دقیق ریشه پروژه
# اگر فایل در backend/app/main.py باشد، سه مرحله به عقب برمی‌گردیم تا به ریشه برسیم
current_file_path = os.path.abspath(__file__)
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
frontend_dir = os.path.join(base_dir, "frontend")

# بررسی وجود پوشه‌های فرانت‌اِند برای جلوگیری از خطا
if os.path.exists(os.path.join(frontend_dir, "src")):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_dir, "src")), name="static")

if os.path.exists(os.path.join(frontend_dir, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="assets")

@app.get("/")
async def serve_index():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": f"index.html not found at {index_path}"}

@app.get("/sw.js")
async def serve_sw():
    path = os.path.join(frontend_dir, "sw.js")
    return FileResponse(path) if os.path.exists(path) else {"error": "sw.js not found"}

@app.get("/manifest.webmanifest")
async def serve_manifest():
    path = os.path.join(frontend_dir, "manifest.webmanifest")
    return FileResponse(path) if os.path.exists(path) else {"error": "manifest not found"}

@app.get("/worker.js")
async def serve_worker():
    path = os.path.join(frontend_dir, "worker.js")
    return FileResponse(path) if os.path.exists(path) else {"error": "worker.js not found"}

# اضافه کردن یک تست برای اطمینان از کارکرد API
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "backend_path": base_dir}
