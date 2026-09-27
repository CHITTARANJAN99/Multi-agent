#!/usr/bin/env bash

# Resolve directory of this script
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Ensure Node.js is in PATH
export PATH="$HOME/.local/node/bin:$PATH"

echo "=========================================================="
echo "🚀 Starting Universal Multi-Agent AI Assistant"
echo "=========================================================="

# Check Python virtualenv
if [ ! -f "$ROOT_DIR/backend/venv/bin/python" ]; then
    echo "Creating Python virtual environment in backend/venv..."
    python3 -m venv "$ROOT_DIR/backend/venv"
    "$ROOT_DIR/backend/venv/bin/pip" install -r "$ROOT_DIR/backend/requirements.txt"
fi

# Clean up any lingering processes on ports 8000 & 3000
pids_8000=$(lsof -ti:8000 2>/dev/null)
if [ -n "$pids_8000" ]; then
    echo "Freeing port 8000 (killing PID: $pids_8000)..."
    kill -9 $pids_8000 2>/dev/null || true
fi

pids_3000=$(lsof -ti:3000 2>/dev/null)
if [ -n "$pids_3000" ]; then
    echo "Freeing port 3000 (killing PID: $pids_3000)..."
    kill -9 $pids_3000 2>/dev/null || true
fi

# Start FastAPI Backend
echo "Starting FastAPI Backend on http://localhost:8000 ..."
(
    cd "$ROOT_DIR/backend"
    export PYTHONPATH=.
    ./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
) &
BACKEND_PID=$!

# Wait for backend healthcheck
echo "Waiting for backend to initialize..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/health >/dev/null 2>&1; then
        echo "✅ Backend is healthy! (All 12 MCP Servers loaded)"
        break
    fi
    sleep 1
done

# Start Next.js Frontend
echo "Starting Next.js Frontend on http://localhost:3000 ..."
(
    cd "$ROOT_DIR/frontend"
    npm run dev -- -p 3000
) &
FRONTEND_PID=$!

echo ""
echo "=========================================================="
echo "✨ System is ready!"
echo "   💻 Frontend Dashboard:   http://localhost:3000"
echo "   📖 Backend Swagger API:  http://localhost:8000/docs"
echo "   🩺 Backend Health Check: http://localhost:8000/health"
echo "=========================================================="
echo "Press Ctrl+C to stop both servers."

cleanup() {
    echo ""
    echo "Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT
wait
