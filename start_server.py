#!/usr/bin/env python3
"""
Start the NG12 Cancer Risk Assessor FastAPI server.
"""
import os
import sys
import webbrowser
import time
from pathlib import Path

def main():
    """Start the server with helpful information."""
    print("🏥 NG12 Cancer Risk Assessor")
    print("=" * 50)
    print("Starting FastAPI server...")
    print()
    
    # Check if required files exist
    required_files = [
        "src/main.py",
        ".env",
        "frontend/index.html"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        print()
        print("Please ensure all files are present before starting the server.")
        return 1
    
    print("✅ All required files present")
    print()
    
    # Display configuration
    print("📋 Configuration:")
    print(f"   - Google Cloud Project: {os.getenv('GOOGLE_CLOUD_PROJECT', 'Not set')}")
    print(f"   - API Host: {os.getenv('API_HOST', '0.0.0.0')}")
    print(f"   - API Port: {os.getenv('API_PORT', '8000')}")
    print(f"   - Vector Store: {os.getenv('VECTOR_STORE_PATH', './data/vector_store')}")
    print()
    
    # Display URLs
    host = os.getenv('API_HOST', '0.0.0.0')
    port = os.getenv('API_PORT', '8000')
    
    if host == '0.0.0.0':
        display_host = 'localhost'
    else:
        display_host = host
    
    print("🌐 Server URLs:")
    print(f"   - Web Interface: http://{display_host}:{port}")
    print(f"   - API Documentation: http://{display_host}:{port}/docs")
    print(f"   - Health Check: http://{display_host}:{port}/health")
    print()
    
    print("🚀 Starting server...")
    print("   Press Ctrl+C to stop the server")
    print()
    
    # Start the server
    try:
        import uvicorn
        uvicorn.run(
            "src.main:app",
            host=host,
            port=int(port),
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
        return 0
    except Exception as e:
        print(f"\n❌ Server failed to start: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())