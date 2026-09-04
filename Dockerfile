FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Use shell form for CMD so $PORT gets resolved dynamically by Render
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}