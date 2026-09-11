FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "alembic upgrade head && python -m backend.app.seed && uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
