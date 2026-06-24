# Parser sidecar — runs the deterministic file work OUTSIDE the Dify sandbox.
# A Dify workflow calls it via an HTTP Request node. Portable: no Dify code here.
FROM python:3.12-slim

WORKDIR /app

# System libs some wheels expect (kept minimal).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY parser/ ./parser/
COPY tests/ ./tests/
COPY app.py .
COPY pytest.ini .

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
