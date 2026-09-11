import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# مسیر فایل‌های فرانت‌اند
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")

# سرو کردن فایل‌های استاتیک
app.mount("/src", StaticFiles(directory=os.path.join(FRONTEND_DIR, "src")), name="src")

@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/{path:path}")
async def serve_static(path: str):
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
