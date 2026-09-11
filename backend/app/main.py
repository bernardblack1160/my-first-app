import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# مسیرهای ریشه
current_file_path = os.path.abspath(__file__)
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))

@app.get("/")
async def serve_index():
    # عیب‌یابی: پیدا کردن فایل‌ها
    file_list = []
    if os.path.exists(base_dir):
        file_list = os.listdir(base_dir)
    
    return {
        "error": "index.html not found",
        "current_base_dir": base_dir,
        "files_in_base_dir": file_list
    }

@app.get("/api/debug")
async def debug_files():
    # یک مسیر کمکی برای دیدن ساختار پوشه‌ها
    structure = {}
    for root, dirs, files in os.walk(base_dir):
        structure[root] = files
        if len(structure) > 10: break # برای جلوگیری از خروجی زیاد
    return structure
