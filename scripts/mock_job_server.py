import http.server
import socketserver
import urllib.parse
import json
import random

# Port to run the server on
PORT = 8080

# Seed the random number generator to ensure reproducibility of mock data
random.seed(42)

# Pool of mock data elements
COMPANIES = [
    {"name": "FinanceCorp", "industry": "Finance"},
    {"name": "WealthTree Advisors", "industry": "Finance"},
    {"name": "Apex Trading Group", "industry": "Finance"},
    {"name": "HealthTech Solutions", "industry": "Healthcare"},
    {"name": "MedData Research", "industry": "Healthcare"},
    {"name": "BioCare Analytics", "industry": "Healthcare"},
    {"name": "Logistics360", "industry": "Logistics"},
    {"name": "SupplyChain.AI", "industry": "Logistics"},
    {"name": "Global Cargo Systems", "industry": "Logistics"},
    {"name": "Quantum AI", "industry": "Tech"},
    {"name": "CloudSync Technologies", "industry": "Tech"},
    {"name": "SaaSify Inc.", "industry": "Tech"},
    {"name": "GreenEnergy Co.", "industry": "Energy"},
    {"name": "EcoPower Systems", "industry": "Energy"}
]

TITLES = [
    "Junior Data Analyst", "Data Analyst", "Senior Data Analyst", 
    "Data Scientist", "Lead Business Intelligence Engineer", 
    "Analytics Specialist", "Machine Learning Analyst", "Operations Data Analyst",
    "Reporting Analyst (Excel & SQL)", "Data Visualization Analyst (Tableau)"
]

LOCATIONS = [
    "New York, NY", "San Francisco, CA", "Chicago, IL", "Austin, TX", 
    "London, UK", "Remote", "Boston, MA", "Seattle, WA"
]

SALARY_TEMPLATES = [
    "${min} - ${max} per year",
    "${min}k - ${max}k",
    "Up to ${max} annually",
    "${min} - ${max}",
    "Salary competitive",
    "Competitive package, around ${avg}k base"
]

# Generate a pool of 120 job postings so we can serve up to 10 pages of 12 jobs each
JOB_POOL = []

# Skill keywords mapping for mock description generation
SKILLS_POOL = [
    ["SQL", "Python", "Power BI"],
    ["SQL", "Tableau", "Excel"],
    ["SQL", "Python", "Tableau", "Machine Learning"],
    ["Excel", "Power BI"],
    ["SQL", "Python", "Machine Learning"],
    ["SQL", "Python", "Excel"],
    ["Python", "Tableau"],
    ["SQL", "Power BI", "Excel"],
    ["SQL", "Python", "Power BI", "Excel", "Machine Learning"],
    ["Excel", "Tableau"]
]

EXP_TEMPLATES = [
    "Requires {years} years of professional experience in analytics.",
    "Looking for {years}+ years of experience in data analytics or business intelligence.",
    "Experience: {years} to {max_years} years in a similar role.",
    "Ideal candidate has {years} years of working with SQL databases.",
    "{years} years minimum required experience.",
    "This is an entry-level role, 0-2 years experience.",
    "Senior level role, requires 5-8 years of experience."
]

def generate_job_pool():
    for i in range(150):
        company_info = random.choice(COMPANIES)
        title = random.choice(TITLES)
        location = random.choice(LOCATIONS)
        
        # Experience setup
        if "Junior" in title or "Entry-level" in title:
            years = random.randint(0, 2)
            exp_text = f"Looking for someone with {years} years of experience."
        elif "Senior" in title or "Lead" in title:
            years = random.randint(5, 8)
            exp_text = f"Candidates must have at least {years} years of analytical experience."
        else:
            years = random.randint(2, 5)
            exp_text = random.choice(EXP_TEMPLATES).format(years=years, max_years=years+2)
            
        # Salary setup
        min_sal = random.randint(50, 130)
        max_sal = min_sal + random.randint(20, 50)
        avg_sal = int((min_sal + max_sal) / 2)
        sal_template = random.choice(SALARY_TEMPLATES)
        salary_text = (sal_template
                       .replace("${min}", f"{min_sal},000")
                       .replace("${max}", f"{max_sal},000")
                       .replace("${avg}", str(avg_sal)))
        
        # Skills setup
        skills = random.choice(SKILLS_POOL)
        skills_str = ", ".join(skills)
        
        # Construct messy description
        description = (
            f"We are seeking a talented {title} to join our {company_info['industry']} team at {company_info['name']}. "
            f"In this role, you will analyze key business metrics, write analytical reports, and deliver insights. "
            f"Technical environment: {skills_str}. Specifically, we expect you to write clean scripts and query databases. "
            f"{exp_text} Additionally, you should have strong communication skills. "
            f"This is a fantastic opportunity to leverage tools like {random.choice(skills)} and grow your career."
        )
        
        # Sometimes throw in tricky text styles
        if random.random() > 0.8:
            description = description.replace("Power BI", "PowerBI").replace("Machine Learning", "ML")
        
        JOB_POOL.append({
            "id": i + 1,
            "title": title,
            "company": company_info["name"],
            "industry": company_info["industry"],
            "location": location,
            "salary": salary_text,
            "description": description
        })

generate_job_pool()

class MockJobBoardHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence default log messages to clean up console output
        pass

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        if path == "/" or path == "/jobs":
            # Pagination logic
            page = int(query.get("page", [1])[0])
            limit = 12
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            
            jobs = JOB_POOL[start_idx:end_idx]
            total_pages = (len(JOB_POOL) + limit - 1) // limit

            if not jobs and page > 1:
                self.send_response(404)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                html = "<html><body><h1>Error 404: No more jobs found</h1></body></html>"
                self.wfile.write(html.encode("utf-8"))
                return

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            # Render HTML layout
            html_parts = []
            html_parts.append("""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>Mock Job Board - Analytics Market</title>
                <style>
                    body { font-family: sans-serif; background-color: #f4f6f9; color: #333; margin: 0; padding: 20px; }
                    .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; border-radius: 8px; margin-bottom: 20px; }
                    .job-card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
                    .job-title { font-size: 1.4em; color: #2980b9; margin-top: 0; }
                    .company-info { font-weight: bold; color: #555; }
                    .meta { color: #888; font-size: 0.9em; margin-bottom: 10px; }
                    .salary { color: #e74c3c; font-weight: bold; }
                    .description { line-height: 1.5; color: #555; }
                    .pagination { text-align: center; margin-top: 30px; font-size: 1.1em; }
                    .pagination a { margin: 0 10px; color: #2980b9; text-decoration: none; font-weight: bold; }
                    .pagination span { font-weight: bold; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Mock Job Board</h1>
                    <p>Simulating 1,000+ live job listings for Data Analysts</p>
                </div>
            \n""")

            for job in jobs:
                html_parts.append(f"""
                <div class="job-card" id="job-{job['id']}">
                    <h2 class="job-title">{job['title']}</h2>
                    <p class="company-info">{job['company']} (Industry: {job['industry']})</p>
                    <p class="meta">
                        Location: <span class="location">{job['location']}</span> | 
                        Salary: <span class="salary">{job['salary']}</span>
                    </p>
                    <div class="description">{job['description']}</div>
                </div>
                """)

            # Add pagination links
            html_parts.append('<div class="pagination">')
            if page > 1:
                html_parts.append(f'<a id="prev-page" href="/jobs?page={page - 1}">&laquo; Previous</a>')
            html_parts.append(f'<span>Page {page} of {total_pages}</span>')
            if page < total_pages:
                html_parts.append(f'<a id="next-page" href="/jobs?page={page + 1}">Next &raquo;</a>')
            html_parts.append('</div>')

            html_parts.append("""
            </body>
            </html>
            """)

            full_html = "\n".join(html_parts)
            self.wfile.write(full_html.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    # Start the HTTP server
    handler = MockJobBoardHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"Mock Job Server running on port {PORT}. Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Stopping mock server...")
            httpd.shutdown()
