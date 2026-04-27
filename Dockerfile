FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends wget \
    && rm -rf /var/lib/apt/lists/*

COPY env/requirements.txt .

RUN pip install --no-cache-dir \
    fastapi==0.135.3 \
    uvicorn==0.44.0 \
    pydantic==2.12.5 \
    python-dotenv==1.2.2 \
    anyio==4.13.0 \
    starlette==1.0.0 \
    click==8.3.2 \
    h11==0.16.0

RUN pip install --no-cache-dir \
    httpx==0.28.1 \
    openai==2.31.0 \
    pymongo==4.7.0 \
    certifi==2026.2.25 \
    httpcore==1.0.9 \
    sniffio==1.3.1 \
    idna==3.11

RUN pip install --no-cache-dir \
    redis==5.0.0 \
    prometheus-client==0.20.0 \
    pytest==9.0.3 \
    annotated-types==0.7.0 \
    typing_extensions==4.15.0

COPY env/ .

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD wget -qO- http://localhost:7860/health || exit 1

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]