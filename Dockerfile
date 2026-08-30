# ---- frontend build ----
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/index.html frontend/vite.config.js ./
COPY frontend/public ./public
COPY frontend/src ./src
RUN npm run build

# ---- backend runtime ----
FROM python:3.11-slim AS runtime
WORKDIR /app

RUN groupadd -r app && useradd -r -g app app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY fixtures/ ./fixtures/
COPY data/ ./data/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

ENV MONDAY_MODE=mock \
    PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE 8000
USER app

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/health', timeout=3)" || exit 1

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
