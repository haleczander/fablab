FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nmap iproute2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

EXPOSE 8001

CMD ["sh", "-c", "uvicorn ${APP_MODULE:-main:app} --host 0.0.0.0 --port ${APP_PORT:-8001}"]
