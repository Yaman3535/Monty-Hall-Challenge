import http.server
import socketserver
import threading
import webbrowser
import os
import sys
import time
import logging
from pathlib import Path

# Third-party dependency: watchdog
# Install it using: pip install watchdog
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("Error: 'watchdog' library not found.")
    print("Please install it using: pip install watchdog")
    sys.exit(1)

# --- Configuration ---
PORT = 3000
HOST = "localhost"
# ---------------------

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class ReloadNotificationHandler(FileSystemEventHandler):
    """A handler for watchdog that prints a notification on any file change."""
    def on_any_event(self, event):
        # We only care about the event type, not the specifics
        if event.is_directory:
            return
        
        # Log the change
        logging.info(f"File changed: {event.src_path}. Reload your browser to see updates.")


def start_server(directory: str):
    """Starts the HTTP server in a background thread."""
    
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def log_message(self, format, *args):
            # Suppress the default noisy logging
            return

    httpd = socketserver.TCPServer((HOST, PORT), Handler)
    
    # Start the server in a daemon thread.
    # This thread will automatically exit when the main program exits.
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    logging.info(f"Server started for directory '{directory}'")
    return httpd


def start_file_watcher(directory: str):
    """Starts the file watcher in a background thread."""
    event_handler = ReloadNotificationHandler()
    observer = Observer()
    observer.schedule(event_handler, directory, recursive=True)
    
    # Start the observer in a daemon thread.
    observer_thread = threading.Thread(target=observer.start)
    observer_thread.daemon = True
    observer_thread.start()
    
    logging.info("File watcher started.")
    return observer


if __name__ == "__main__":
    # The script should be run from the directory it needs to serve.
    serve_directory = os.getcwd()
    
    # A simple validation to ensure we are in a web app's dist folder.
    if not Path("index.html").exists():
        logging.warning("Warning: 'index.html' not found in the current directory.")
        logging.warning("Please make sure you are running this script from your 'dist' folder.")
        time.sleep(3) # Give user time to read the warning.

    logging.info("--- Professional Web App Server ---")
    
    try:
        # 1. Start the Server
        server = start_server(serve_directory)
        
        # 2. Start the File Watcher
        watcher = start_file_watcher(serve_directory)
        
        # 3. Open the Web Browser
        url = f"http://{HOST}:{PORT}"
        logging.info(f"Opening browser at {url}")
        webbrowser.open(url)
        
        # 4. Wait for user to exit (Ctrl+C)
        print("\n" + "="*40)
        print(f"  Server is live at: {url}")
        print("  Watching for file changes...")
        print("  Press Ctrl+C to stop the server.")
        print("="*40 + "\n")
        
        while True:
            time.sleep(1)

    except OSError as e:
        if "address already in use" in str(e).lower():
            logging.error(f"FATAL: Port {PORT} is already in use by another application.")
            logging.error("Please close the other application or choose a different port.")
        else:
            logging.error(f"An OS error occurred: {e}")
        sys.exit(1)
        
    except KeyboardInterrupt:
        logging.info("Ctrl+C received, shutting down server and watcher...")
        watcher.stop()
        watcher.join()
        server.shutdown()
        server.server_close()
        logging.info("Shutdown complete. Goodbye!")
        
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        
    finally:
        sys.exit(0)
