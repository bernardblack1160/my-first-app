import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# پیدا کردن مسیر اصلی پروژه (Root) بر اساس موقعیت این فایل
# چون main.py در backend/app/ است، دو مرحله به عقب برمی‌گردیم تا به src برسیم
current_file_path = os.path.abspath(__file__)
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
frontend_dir = os.path.join(base_dir, "frontend")

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

# سرو کردن فایل‌های استاتیک از پوشه frontend
if os.path.exists(frontend_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="assets")
    # اگر پوشه src داخل frontend بود، اینجا اصلاح می‌شود، اما طبق گزارش شما فایل‌ها در frontend هستند
else:
    print(f"Warning: frontend directory not found at {frontend_dir}")

@app.get("/")
async def serve_index():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": f"index.html not found at {index_path}"}

# مسیرهای API شما در اینجا ادامه می‌یابد...
