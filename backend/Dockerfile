FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY frontend ./frontend
COPY alembic.ini ./alembic.ini
ENV PYTHONPATH=/app
CMD ["sh", "-c", "alembic upgrade head && python -m backend.app.seed && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
