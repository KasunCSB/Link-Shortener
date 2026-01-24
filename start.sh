#!/usr/bin/env bash
set -euo pipefail

# Start frontend (Node) and backend (Uvicorn) in one container
node /app/frontend/server.js &
exec uvicorn app.main:app --host 0.0.0.0 --port 17321
