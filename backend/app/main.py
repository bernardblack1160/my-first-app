import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Lila API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def resolve_frontend_dir() -> Path:
    base_dir = Path(__file__).resolve().parents[2]
    candidates = [
        base_dir / "frontend",
        base_dir / "backend" / "frontend",
        Path("/opt/render/project/src/frontend") # Render specific path fallback
    ]
    for candidate in candidates:
        if (candidate / "index.html").exists():
            return candidate
    raise RuntimeError(f"Frontend directory not found. Checked: {candidates}")

frontend_dir = resolve_frontend_dir()

# Debugging logs for Render console
print(f"DEBUG: Base Directory: {Path(__file__).resolve().parents[2]}")
print(f"DEBUG: Frontend Directory Found: {frontend_dir}")
print(f"DEBUG: Exists: {frontend_dir.exists()}")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Serve specific service workers and manifests
@app.get("/worker.js")
async def get_worker():
    return FileResponse(frontend_dir / "sw.js", media_type="application/javascript")

@app.get("/manifest.webmanifest")
async def get_manifest():
    return FileResponse(frontend_dir / "manifest.webmanifest")

# Serve Static Files (src)
app.mount("/src", StaticFiles(directory=frontend_dir / "src"), name="src")

@app.get("/")
async def serve_frontend():
    return FileResponse(frontend_dir / "index.html")

@app.get("/{path:path}")
async def serve_static(path: str):
    # Check if it's a file in frontend
    file_path = frontend_dir / path
    if file_path.is_file():
        return FileResponse(file_path)
    # Fallback to index.html for SPA routing
    return FileResponse(frontend_dir / "index.html")
