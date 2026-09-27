#!/usr/bin/env bash

echo "Stopping servers on ports 8000 and 3000..."

pids_8000=$(lsof -ti:8000 2>/dev/null)
if [ -n "$pids_8000" ]; then
    echo "Stopping Backend process (PID: $pids_8000)..."
    kill -9 $pids_8000 2>/dev/null || true
fi

pids_3000=$(lsof -ti:3000 2>/dev/null)
if [ -n "$pids_3000" ]; then
    echo "Stopping Frontend process (PID: $pids_3000)..."
    kill -9 $pids_3000 2>/dev/null || true
fi

echo "✅ All servers stopped."
