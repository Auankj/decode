#!/bin/bash

# Cookie Licking Detector - Production Startup Script
# This script starts all required services for production deployment

set -e

echo "🚀 Starting Cookie Licking Detector Production Environment"
echo "=================================================="

# Check if PostgreSQL is running
if ! brew services list | grep -q "postgresql@15.*started"; then
    echo "📊 Starting PostgreSQL..."
    brew services start postgresql@15
    sleep 2
fi

# Check if Redis is running
if ! brew services list | grep -q "redis.*started"; then
    echo "🔴 Starting Redis..."
    brew services start redis
    sleep 2
fi

# Set PostgreSQL path for this session
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"

echo "✅ Database services started"
echo ""

# Start Celery worker in background
echo "🏃‍♂️ Starting Celery worker..."
cd "$(dirname "$0")"
celery -A app.core.celery worker --loglevel=info &
CELERY_PID=$!

echo "✅ Celery worker started (PID: $CELERY_PID)"
echo ""

# Start FastAPI server
echo "🌐 Starting FastAPI server..."
echo "API will be available at: http://localhost:8000"
echo "API Documentation at: http://localhost:8000/docs"
echo "Health Check at: http://localhost:8000/health"
echo "Metrics at: http://localhost:8000/metrics"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Trap to cleanup on exit
trap 'echo "🛑 Stopping services..."; kill $CELERY_PID 2>/dev/null; exit 0' INT TERM

# Start the main application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload