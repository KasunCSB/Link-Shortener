#!/usr/bin/env bash
set -euo pipefail

# Start frontend (Node) and backend (Uvicorn) in one container
node /app/frontend/server.js &
uvicorn app.main:app --host 127.0.0.1 --port 8001 &

# Nginx runs in the foreground and proxies to Node/Uvicorn
exec nginx -g "daemon off;"
