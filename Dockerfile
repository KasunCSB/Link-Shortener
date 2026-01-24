FROM node:20-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=3000

WORKDIR /app

# Install Python and backend dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip nginx \
  && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN python3 -m pip install --no-cache-dir --break-system-packages -r /app/backend/requirements.txt

# Copy app code and static frontend
COPY backend /app/backend
COPY frontend/package.json /app/frontend/package.json
COPY frontend/package-lock.json /app/frontend/package-lock.json
RUN cd /app/frontend && npm ci --omit=dev
COPY frontend/public /app/frontend/public
COPY frontend/server.js /app/frontend/server.js
COPY start.sh /app/start.sh
COPY nginx.conf /etc/nginx/nginx.conf
RUN chmod +x /app/start.sh

WORKDIR /app/backend

EXPOSE 8000

CMD ["bash", "/app/start.sh"]
