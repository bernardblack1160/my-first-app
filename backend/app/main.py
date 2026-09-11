import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

print(f"DEBUG: Working Directory: {os.getcwd()}")
print(f"DEBUG: Frontend Path: {FRONTEND_DIR}")
print(f"DEBUG: Exists: {FRONTEND_DIR.exists()}")

app.mount("/src", StaticFiles(directory=FRONTEND_DIR / "src"), name="src")

@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/{path:path}")
async def serve_static(path: str):
    file_path = FRONTEND_DIR / path
    if file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(FRONTEND_DIR / "index.html")
