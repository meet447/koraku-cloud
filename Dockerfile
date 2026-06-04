FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY koraku ./koraku
COPY koraku_cloud ./koraku_cloud

RUN pip install --no-cache-dir -e ".[all]" \
    && pip install --no-cache-dir -e ./koraku_cloud

ENV KORAKU_SERVER_APP=cloud

ENV HOST=0.0.0.0
ENV PORT=8000
ENV UVICORN_RELOAD=false
ENV WEB_CONCURRENCY=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "koraku_cloud.app:app", "--host", "0.0.0.0", "--port", "8000"]
