import urllib.request
import urllib.error
import sqlite3
import random
import time
import os
from html.parser import HTMLParser

# Database Configuration
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "job_market.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "schema.sql")

# Scraper Target
BASE_URL = "http://localhost:8080/jobs"

# Human emulation parameters
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
]

class JobBoardHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.jobs = []
        self.current_job = None
        self.current_field = None
        self.in_field = False
        self.card_depth = -1  # Tracks depth inside a job card

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        # If we encounter a job-card, initialize our job dictionary
        if tag == "div" and attrs_dict.get("class") == "job-card":
            self.current_job = {
                "title": "",
                "company": "",
                "location": "",
                "salary": "",
                "description": ""
            }
            self.card_depth = 0
            return

        if self.current_job is not None:
            self.card_depth += 1
            if tag == "h2" and attrs_dict.get("class") == "job-title":
                self.current_field = "title"
                self.in_field = True
            elif tag == "p" and attrs_dict.get("class") == "company-info":
                self.current_field = "company"
                self.in_field = True
            elif tag == "span" and attrs_dict.get("class") == "location":
                self.current_field = "location"
                self.in_field = True
            elif tag == "span" and attrs_dict.get("class") == "salary":
                self.current_field = "salary"
                self.in_field = True
            elif tag == "div" and attrs_dict.get("class") == "description":
                self.current_field = "description"
                self.in_field = True

    def handle_endtag(self, tag):
        if self.current_job is not None:
            if tag == "div" and self.card_depth == 0:
                # Finished parsing the job-card
                # Clean company string
                if self.current_job["company"]:
                    self.current_job["company"] = self.current_job["company"].strip()
                # Clean descriptions
                if self.current_job["description"]:
                    self.current_job["description"] = self.current_job["description"].strip()
                
                self.jobs.append(self.current_job)
                self.current_job = None
                self.card_depth = -1
            else:
                self.card_depth -= 1
                self.in_field = False
                self.current_field = None

    def handle_data(self, data):
        if self.current_job is not None and self.in_field:
            clean_data = data.strip()
            if clean_data:
                if self.current_job[self.current_field]:
                    self.current_job[self.current_field] += " " + clean_data
                else:
                    self.current_job[self.current_field] = clean_data

def init_db():
    """Initializes the SQLite database using schema.sql if database is new."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if table staged_jobs exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='staged_jobs';")
    exists = cursor.fetchone()
    
    if not exists:
        print("[DB] Database not initialized. Applying schema.sql...")
        if os.path.exists(SCHEMA_PATH):
            with open(SCHEMA_PATH, 'r') as f:
                schema_sql = f.read()
                cursor.executescript(schema_sql)
            conn.commit()
            print("[DB] Schema applied successfully.")
        else:
            print(f"[DB] Error: schema.sql not found at {SCHEMA_PATH}")
    else:
        # Clear existing raw stagings before a new run
        cursor.execute("DELETE FROM staged_jobs WHERE is_processed = 0;")
        conn.commit()
        print("[DB] Connected to database. Cleaned unprocessed staging table.")
        
    conn.close()

def save_jobs_to_staging(jobs):
    """Saves raw job listings into the staged_jobs database table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    inserted = 0
    for job in jobs:
        try:
            cursor.execute("""
                INSERT INTO staged_jobs (title, company, location, salary_raw, description_raw)
                VALUES (?, ?, ?, ?, ?)
            """, (job["title"], job["company"], job["location"], job["salary"], job["description"]))
            inserted += 1
        except Exception as e:
            print(f"[Error] Failed to insert staged job: {e}")
            
    conn.commit()
    conn.close()
    return inserted

def scrape_job_board():
    """Scrapes the paginated job board and stores them in database."""
    print("=========================================")
    print("       STARTING JOB MARKET SCRAPER       ")
    print("=========================================")
    print(f"Targeting: {BASE_URL}")
    print(f"Database: {DB_PATH}")
    
    init_db()
    
    page = 1
    total_scraped = 0
    
    while True:
        url = f"{BASE_URL}?page={page}"
        print(f"[Scraper] Fetching Page {page}...")
        
        # Human emulation: Random User-Agent
        user_agent = random.choice(USER_AGENTS)
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': user_agent}
        )
        
        try:
            # Human emulation: Random delays (0.5 to 1.5 seconds)
            delay = random.uniform(0.5, 1.5)
            time.sleep(delay)
            
            with urllib.request.urlopen(req) as response:
                html_data = response.read().decode('utf-8')
                
                # Parse HTML content
                parser = JobBoardHTMLParser()
                parser.feed(html_data)
                
                if not parser.jobs:
                    print(f"[Scraper] No job postings found on page {page}. Stopping.")
                    break
                    
                inserted_count = save_jobs_to_staging(parser.jobs)
                print(f"[Scraper] Page {page} processed. Scraped {len(parser.jobs)} jobs. Inserted {inserted_count} into staging.")
                total_scraped += inserted_count
                
                page += 1
                
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"[Scraper] Page {page} returned 404 (No more pages). Scraping finished.")
            else:
                print(f"[Scraper] HTTP Error {e.code} occurred: {e.reason}")
            break
        except urllib.error.URLError as e:
            print(f"[Scraper] Connection error: {e.reason}")
            print("[Scraper] Make sure the mock job server is running (python scripts/mock_job_server.py)")
            break
        except Exception as e:
            print(f"[Scraper] An unexpected error occurred: {e}")
            break
            
    print("=========================================")
    print(f" SCRAPING COMPLETE. TOTAL STAGED: {total_scraped} ")
    print("=========================================")
    return total_scraped

if __name__ == "__main__":
    scrape_job_board()
