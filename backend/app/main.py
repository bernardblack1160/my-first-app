import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# چون پوشه frontend الان داخل backend هست، مسیرش میشه دقیقاً کنار این فایل
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

# مستقیم به زیرمجموعه‌های backend اشاره می‌کنیم
app.mount("/src", StaticFiles(directory=os.path.join(FRONTEND_DIR, "src")), name="src")
app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

