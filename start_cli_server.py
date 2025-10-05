#!/usr/bin/env python3
"""
Start the Cookie Licking Detector backend server in a minimal mode that works with CLI
This version uses mocked database to allow testing of the CLI
"""
import os
import sys
import threading
import time
import signal
import requests
from unittest.mock import patch, MagicMock
from contextlib import contextmanager

# Add the project path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use test environment
os.environ.setdefault('ENVIRONMENT', 'test')
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost:5432/testdb')

def start_server_with_mocked_db():
    """Start the server with mocked database connections"""
    
    with patch('app.db.database.get_async_session'), \
         patch('app.db.database.create_tables'), \
         patch('app.db.database.close_db'), \
         patch('sqlalchemy.ext.asyncio.create_async_engine'), \
         patch('app.db.database.async_sessionmaker'), \
         patch('app.core.monitoring.health_checker.check_database'), \
         patch('app.core.config.get_settings') as mock_settings:

        from app.core.config import Settings
        mock_settings_instance = Settings()
        mock_settings_instance.DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///./test.db')
        mock_settings_instance.ENVIRONMENT = 'test'
        mock_settings_instance.DEBUG = True
        mock_settings_instance.API_PORT = 8000
        mock_settings.return_value = mock_settings_instance

        from app.main import app
        import uvicorn
        
        print("Starting Cookie Licking Detector server on port 8000...")
        print("Server is running with mocked database for CLI testing")
        print("Press Ctrl+C to stop the server")
        
        # Run the server
        uvicorn.run(app, host='127.0.0.1', port=8000, log_level='warning')

def main():
    print("🚀 Starting Cookie Licking Detector Backend Server...")
    print("This server is configured for CLI testing with mocked database")
    
    # Start server in a thread
    server_thread = threading.Thread(target=start_server_with_mocked_db, daemon=True)
    server_thread.start()
    
    # Wait a bit for server to start
    time.sleep(3)
    
    # Test that server is responding
    print("\n🔍 Testing server connectivity...")
    try:
        response = requests.get('http://127.0.0.1:8000/health', timeout=5)
        if response.status_code == 200:
            print(f"✅ Server is running and responding to health check")
            print(f"✅ Health check response: {response.json().get('status', 'unknown')}")
        else:
            print(f"❌ Server responded with status {response.status_code}")
    except Exception as e:
        print(f"❌ Could not connect to server: {e}")
        return
    
    print(f"\n🌐 Server is accessible at: http://127.0.0.1:8000")
    print("📱 You can now use the CLI to interact with the server:")
    print("   cookie-detector status")
    print("   cookie-detector repos list")
    print("   cookie-detector claims list")
    print("   etc.")
    
    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")

if __name__ == "__main__":
    main()