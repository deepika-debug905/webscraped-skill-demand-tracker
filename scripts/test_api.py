import os
import sys
import time
import threading
import json
import socketserver
import urllib.request
import urllib.error

# Ensure scripts directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api_server import app
import uvicorn

TEST_PORT = 8001
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"

def start_test_server():
    """Starts the FastAPI server in a background thread."""
    try:
        config = uvicorn.Config(app, host="127.0.0.1", port=TEST_PORT, log_level="warning")
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        print(f"[Test] Background FastAPI test server started on {BASE_URL}")
        return server
    except Exception as e:
        print(f"[Test Error] Could not start FastAPI test server: {e}")
        sys.exit(1)

def query_endpoint(path, method="GET", body=None):
    """Sends a request to the test server and returns parsed JSON response."""
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    data = json.dumps(body).encode("utf-8") if body else None
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Read the error details
        error_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(error_body)
        except Exception:
            return e.code, error_body
    except Exception as e:
        print(f"[Test Error] HTTP request failed: {e}")
        return 500, str(e)

def run_tests():
    print("=========================================================")
    print("       STARTING INTEGRATION TESTS FOR FULL-STACK API     ")
    print("=========================================================")
    
    # Wait for server initialization
    time.sleep(1.5)
    
    errors = 0
    
    # Test 1: Check Metadata endpoint
    print("[Test 1] Querying /api/meta...")
    status, res = query_endpoint("/api/meta")
    if status == 200 and "locations" in res and "industries" in res:
        print(f"  [Pass] Metadata fetched successfully. Found {len(res['locations'])} locations.")
    else:
        print(f"  [Fail] Metadata check failed. Status: {status}, Response: {res}")
        errors += 1
        
    # Test 2: Check Jobs Listing endpoint
    print("[Test 2] Querying /api/jobs (Page 1, Limit 2)...")
    status, res = query_endpoint("/api/jobs?page=1&limit=2")
    if status == 200 and "jobs" in res and len(res["jobs"]) <= 2:
        print(f"  [Pass] Jobs list fetched successfully. Found {len(res['jobs'])} jobs.")
    else:
        print(f"  [Fail] Jobs endpoint failed. Status: {status}, Response: {res}")
        errors += 1

    # Test 3: Check Jobs Filtering by Location
    if status == 200 and len(res["jobs"]) > 0:
        target_loc = res["jobs"][0]["location"]
        print(f"[Test 3] Filtering jobs by location: '{target_loc}'...")
        status, filter_res = query_endpoint(f"/api/jobs?location={urllib.parse.quote(target_loc)}")
        if status == 200 and all(j["location"] == target_loc for j in filter_res["jobs"]):
            print("  [Pass] Location filtering functions correctly.")
        else:
            print(f"  [Fail] Location filtering failed. Status: {status}, Response: {filter_res}")
            errors += 1

    # Test 4: Check Analytics endpoint
    print("[Test 4] Querying /api/analytics...")
    status, res = query_endpoint("/api/analytics")
    if status == 200 and "kpis" in res and "skills_demand" in res:
        print(f"  [Pass] Analytics aggregate data loaded. Total openings count: {res['kpis']['total_jobs']}")
    else:
        print(f"  [Fail] Analytics endpoint failed. Status: {status}, Response: {res}")
        errors += 1

    # Test 5: Check Resume salary predictor
    print("[Test 5] Querying /api/predict-salary...")
    payload = {
        "resume_text": "I am an analyst specialized in writing SQL queries and Python scripting. Experienced with Excel.",
        "experience_years": 4
    }
    status, res = query_endpoint("/api/predict-salary", method="POST", body=payload)
    if status == 200 and "estimated_salary" in res and res["match_percent"] > 0:
        print(f"  [Pass] Salary predicted: ${res['estimated_salary']:,}. Match percent: {res['match_percent']}%")
    else:
        print(f"  [Fail] Predict-salary endpoint failed. Status: {status}, Response: {res}")
        errors += 1

    # Test 6: Check SQL playground (Safe select query)
    print("[Test 6] Querying /api/sql/query (Valid SELECT)...")
    payload = {
        "query": "SELECT COUNT(*) as cnt, experience_level FROM job_postings GROUP BY experience_level;"
    }
    status, res = query_endpoint("/api/sql/query", method="POST", body=payload)
    if status == 200 and res.get("success") is True:
        print(f"  [Pass] SQL SELECT compiled. Elapsed: {res['elapsed_ms']}ms. Rows returned: {res['row_count']}")
    else:
        print(f"  [Fail] SQL query compilation failed. Status: {status}, Response: {res}")
        errors += 1

    # Test 7: Check SQL sandbox security constraints (Blocked UPDATE statement)
    print("[Test 7] Querying /api/sql/query (Malicious UPDATE block)...")
    payload = {
        "query": "UPDATE job_postings SET salary_avg = 999999 WHERE job_id = 1;"
    }
    status, res = query_endpoint("/api/sql/query", method="POST", body=payload)
    # Check if 400 Bad Request returned by validation OR success=False returned by SQLite read-only error
    if status == 400 or (status == 200 and res.get("success") is False):
        msg = res.get("detail") if status == 400 else res.get("error")
        print(f"  [Pass] Destructive query successfully blocked! Reason: {msg}")
    else:
        print(f"  [Fail] Destructive write query was NOT blocked! Status: {status}, Response: {res}")
        errors += 1

    print("=========================================================")
    if errors == 0:
        print("          ALL INTEGRATION TESTS PASSED SUCCESSFULLY!     ")
    else:
        print(f"          TEST RUN COMPLETED WITH {errors} FAILURE(S)    ")
    print("=========================================================")
    return errors == 0

if __name__ == "__main__":
    # Start server
    server = start_test_server()
    
    # Run tests
    success = run_tests()
    
    # Stop server and exit
    print("[Test] Shutting down test server...")
    sys.exit(0 if success else 1)
