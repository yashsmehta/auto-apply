#!/usr/bin/env python3
"""Test script to verify web interface functionality"""
import requests
import time
import subprocess
import sys
import os

def test_web_server():
    """Test that the web server starts and responds correctly"""
    # Start the server in a subprocess
    env = os.environ.copy()
    process = subprocess.Popen(
        ['uv', 'run', 'python', 'main.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    
    # Give the server time to start
    time.sleep(3)
    
    try:
        # Test the main page
        response = requests.get('http://localhost:5000')
        assert response.status_code == 200
        assert 'Auto-Apply' in response.text
        print("✓ Web server is running and responding")
        
        # Test the health endpoint
        response = requests.get('http://localhost:5000/api/health')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        print("✓ API health check passed")
        
        print("\nWeb interface is working correctly!")
        print("You can now run: uv run python main.py")
        print("The browser will open automatically to http://localhost:5000")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nMake sure no other process is using port 5000")
        sys.exit(1)
    finally:
        # Clean up - terminate the server
        process.terminate()
        process.wait()


if __name__ == "__main__":
    test_web_server()