#!/bin/bash

# RAG Cold Case Detective - Implementation Launch Script

# Function to kill processes on exit
cleanup() {
    echo "Shutting down services..."
    kill $(jobs -p) 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

echo "---------------------------------------------------"
echo "🕵️‍♂️  Starting RAG Cold Case Detective System..."
echo "---------------------------------------------------"

# 1. Activate Virtual Environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "❌ Error: Virtual environment not found. Please run 'python3 -m venv .venv' and install requirements."
    exit 1
fi

# 2. Start Backend API
echo "Starting Backend API (Port 8000)..."
if lsof -ti:8000; then
    echo "⚠️  Port 8000 is occupied. Attempting to clear..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
fi

python3 api.py &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"

# 3. Start Frontend
echo "Starting Frontend Interface..."
cd frontend
npm run dev &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"

echo "---------------------------------------------------"
echo "🚀 System is Live!"
echo "---------------------------------------------------"
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "---------------------------------------------------"
echo "Press Ctrl+C to stop all services."

# Wait for processes
wait
