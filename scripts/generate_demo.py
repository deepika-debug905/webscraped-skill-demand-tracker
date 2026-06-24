import os
import sys
import time
import threading
import socketserver
import urllib.request
import urllib.error

# Ensure scripts directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mock_job_server import MockJobBoardHandler, PORT
from scraper import scrape_job_board, DB_PATH, SCHEMA_PATH
from data_cleaning import run_cleaning_pipeline

def start_server_in_thread():
    """Starts the mock HTTP server in a background daemon thread."""
    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True
        
    try:
        httpd = ReusableTCPServer(("", PORT), MockJobBoardHandler)
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()
        print(f"[Demo] Background Mock Job Server started on port {PORT}.")
        return httpd
    except Exception as e:
        print(f"[Demo Error] Could not start mock server on port {PORT}: {e}")
        print("[Demo Error] Check if another process is using port 8080.")
        sys.exit(1)

def main():
    print("=====================================================================")
    print("        JOB MARKET & SKILL DEMAND PREDICTOR: PIPELINE DEMO           ")
    print("=====================================================================")
    print("This script will execute the entire ETL pipeline end-to-end:")
    print("1. Start a local HTTP server serving mock job pages.")
    print("2. Scrape paginated listings using automated delays & custom headers.")
    print("3. Stage raw crawled jobs in a local SQLite database.")
    print("4. Clean descriptions, parse salaries/experience/skills using Regex.")
    print("5. Normalize and store data in 3NF relational tables.")
    print("6. Train a Multiple Linear Regression model in pure Python.")
    print("7. Export metrics and model weights for the interactive portfolio dashboard.")
    print("=====================================================================\n")

    # Start mock server
    httpd = start_server_in_thread()
    time.sleep(1)  # Give the server a second to initialize

    # Test server connectivity
    try:
        urllib.request.urlopen(f"http://localhost:{PORT}/jobs")
        print("[Demo] Connection test to mock server succeeded.")
    except Exception as e:
        print(f"[Demo Error] Failed to connect to mock server: {e}")
        httpd.shutdown()
        sys.exit(1)

    try:
        # Run scraper
        total_staged = scrape_job_board()
        
        if total_staged > 0:
            # Run cleaning pipeline
            run_cleaning_pipeline()
            
            print("\n=====================================================================")
            print("                       DEMO RUN COMPLETED                            ")
            print("=====================================================================")
            print(f" SQLite Database generated at: {DB_PATH}")
            print(f" Dashboard Data written to: dashboard/dashboard_data.json")
            print(f" Trained ML model weights written to: database/salary_model.json")
            print("\nTo view the full-stack interactive web application:")
            print("1. Install requirements if you haven't already:")
            print("   pip install -r requirements.txt")
            print("2. Start the FastAPI API server:")
            print("   uvicorn scripts.api_server:app --reload --port 8000")
            print("3. Open your browser and navigate to:")
            print("   http://localhost:8000")
            print("   (This runs the dashboard, dynamic filters, job explorer, and SQL playground!)")
            print("=====================================================================")
        else:
            print("[Demo Error] Scraper finished but no jobs were staged. ETL cancelled.")

    except Exception as e:
        print(f"[Demo Error] Pipeline execution failed: {e}")
    finally:
        print("[Demo] Shutting down mock job server...")
        httpd.shutdown()
        print("[Demo] Server stopped. Exit.")

if __name__ == "__main__":
    main()
