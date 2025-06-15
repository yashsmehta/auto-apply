"""Main module for auto-apply - launches web interface"""
import os
import sys
import webbrowser
from threading import Timer


def open_browser():
    """Open web browser after a short delay"""
    webbrowser.open('http://localhost:5001')


def main():
    """Main function - launches the web interface"""
    print("Starting Auto-Apply Web Interface...")
    print("\nThe web interface will open in your browser shortly.")
    print("If it doesn't open automatically, visit: http://localhost:5001")
    print("\nPress Ctrl+C to stop the server.\n")
    
    # Schedule browser opening after 1.5 seconds
    Timer(1.5, open_browser).start()
    
    # Import and run the Flask app
    from web.app import app
    
    # Ensure output directory exists
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Run the Flask server
    try:
        app.run(
            host='127.0.0.1',
            port=5001,
            debug=False,  # Disable debug in production
            use_reloader=False  # Disable reloader to prevent double browser opening
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        sys.exit(0)
    except OSError as e:
        if "Address already in use" in str(e):
            print("\nError: Port 5001 is already in use!")
            print("Please close any other applications using this port.")
            print("\nAlternatively, you can access the existing server at: http://localhost:5001")
        else:
            print(f"\nError starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()