#!/usr/bin/env python3
"""
Start the complete Cookie Licking Detector backend
"""
import subprocess
import time
import os
import signal
import sys

def cleanup_processes():
    """Kill any existing processes"""
    print("🧹 Cleaning up existing processes...")
    subprocess.run(['pkill', '-f', 'uvicorn'], capture_output=True)
    subprocess.run(['pkill', '-f', 'celery'], capture_output=True)
    time.sleep(2)

def start_services():
    """Start all backend services"""
    print("🚀 Starting Cookie Licking Detector Backend...")
    print("=" * 60)
    
    # Start FastAPI server
    print("📡 Starting FastAPI server on port 8000...")
    fastapi_process = subprocess.Popen([
        'python3', '-m', 'uvicorn', 'app.main:app', 
        '--host', '0.0.0.0', '--port', '8000', '--reload'
    ])
    
    # Wait a bit for FastAPI to start
    time.sleep(3)
    
    # Start Celery worker
    print("⚙️ Starting Celery worker...")
    celery_process = subprocess.Popen([
        'python3', '-m', 'celery', '-A', 'app.core.celery_app', 'worker',
        '--loglevel=info', '--pool=solo'
    ])
    
    print("\n✅ Backend services started successfully!")
    print(f"🌐 FastAPI server: http://localhost:8000")
    print(f"📚 API docs: http://localhost:8000/docs")
    print(f"🏥 Health check: http://localhost:8000/health")
    print(f"📊 Metrics: http://localhost:8000/metrics")
    print("\nPress Ctrl+C to stop all services")
    
    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
        fastapi_process.terminate()
        celery_process.terminate()
        time.sleep(2)
        try:
            fastapi_process.kill()
            celery_process.kill()
        except:
            pass
        print("✅ All services stopped")

if __name__ == "__main__":
    cleanup_processes()
    start_services()