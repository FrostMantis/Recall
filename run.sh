#!/bin/bash
ROOT="/mnt/projects-sys2/Coding/01-Projects/Recall"

# Start backend (MariaDB; connection config from .env)
cd "$ROOT/backend"
uvicorn main:app --reload --host 0.0.0.0 &
BACKEND_PID=$!

# Start frontend
python3 -m http.server 3000 --bind 0.0.0.0 --directory "$ROOT/frontend" &
FRONTEND_PID=$!

echo "Backend: http://0.0.0.0:8000"
echo "Frontend: http://0.0.0.0:3000"

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
