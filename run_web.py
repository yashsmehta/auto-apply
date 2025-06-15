#!/usr/bin/env python3
"""
Script to run the Auto-Apply web interface
"""

import sys
import os

# Add the parent directory to the path so we can import the web module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web.app import app

if __name__ == '__main__':
    print("Starting Auto-Apply Web Interface...")
    print("Server running at http://localhost:5000")
    print("Press Ctrl+C to stop")
    
    # Create output directory if it doesn't exist
    os.makedirs('output', exist_ok=True)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )