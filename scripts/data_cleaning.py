import sqlite3
import re
import os
import json

# Database Configuration
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "job_market.db")
DASHBOARD_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "dashboard_data.json")
DASHBOARD_JS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "dashboard_data.js")

def parse_company_info(company_raw):
    """
    Parses company name and industry from a string like "FinanceCorp (Industry: Finance)".
    Returns (company_name, industry)
    """
    # Pattern to match "Name (Industry: IndustryName)"
    match = re.match(r"^(.+?)\s*\(Industry:\s*(.+?)\)$", company_raw)
    if match:
        name = match.group(1).strip()
        industry = match.group(2).strip()
        return name, industry
    return company_raw.strip(), "Unspecified"

def parse_salary(salary_raw):
    """
    Cleans and extracts salary_min, salary_max, and salary_avg from messy text.
    Handles:
    - "$80,000 - $115,000 per year"
    - "$90k - $120k"
    - "Up to $150,000"
    - "$45 - $65 an hour"
    - "Competitive package, around 95k base"
    - "90 - 120" (implicit thousands)
    Returns (salary_min, salary_max, salary_avg) or (None, None, None)
    """
    if not salary_raw or "competitive" in salary_raw.lower() or "salary" in salary_raw.lower() and len(salary_raw) < 15:
        return None, None, None

    text = salary_raw.lower()
    
    # 1. Check for hourly rate
    is_hourly = False
    if "hour" in text or "hr" in text or "/hr" in text or "an hour" in text:
        is_hourly = True

    # Remove currency symbols and commas
    text = text.replace("$", "").replace(",", "")

    # Replace 'k' with '000'
    text = re.sub(r'(\d+)\s*k', r'\g<1>000', text)

    # Extract all numbers
    numbers = [int(n) for n in re.findall(r'\d+', text)]

    if not numbers:
        return None, None, None

    min_sal = None
    max_sal = None

    if len(numbers) >= 2:
        # Standard range e.g. "80000 - 120000"
        min_sal = min(numbers[0], numbers[1])
        max_sal = max(numbers[0], numbers[1])
    else:
        # Single number e.g. "Up to 150000"
        val = numbers[0]
        if "up to" in text or "maximum" in text or "max" in text:
            max_sal = val
            min_sal = int(val * 0.7) # Estimate min as 70% of max
        else:
            min_sal = val
            max_sal = val

    # Handle hourly to salary conversion (multiply by 2,000 hours/year)
    if is_hourly:
        # Check if numbers were already in thousands (which would be weird for hourly, e.g. 50k, but let's check)
        if min_sal < 1000:
            min_sal *= 2000
        if max_sal < 1000:
            max_sal *= 2000
    else:
        # Handle implicit thousands (e.g. "90 - 120" -> "90000 - 120000")
        if min_sal and min_sal < 1000:
            min_sal *= 1000
        if max_sal and max_sal < 1000:
            max_sal *= 1000

    # Sanity checks
    if min_sal and min_sal < 10000:  # If it's still way too low, it's garbage data
        return None, None, None

    avg_sal = int((min_sal + max_sal) / 2) if (min_sal and max_sal) else None
    return float(min_sal), float(max_sal), float(avg_sal)

def parse_experience(description_text, title_text):
    """
    Parses experience required from job description and title.
    Returns (experience_years, experience_level)
    """
    desc_lower = description_text.lower()
    title_lower = title_text.lower()
    
    years = None

    # Search for patterns like "1-3 years", "2+ years", "5 years"
    patterns = [
        r'\b(\d+)\s*-\s*(\d+)\s*years?\b',
        r'\b(\d+)\+\s*years?\b',
        r'\b(\d+)\s*years?\s*(?:of\s*)?experience\b',
        r'\bexperience\s*required\s*:\s*(\d+)\s*years?\b'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, desc_lower)
        if matches:
            first_match = matches[0]
            if isinstance(first_match, tuple):
                # E.g. ("1", "3") -> average 2 years
                min_yr = int(first_match[0])
                max_yr = int(first_match[1])
                years = int((min_yr + max_yr) / 2)
            else:
                years = int(first_match)
            break

    # Determine experience level
    if years is not None:
        if years <= 2:
            level = "Entry"
        elif years <= 5:
            level = "Mid"
        else:
            level = "Senior"
    else:
        # Fallback to keyword matching in title or description
        if any(w in title_lower or w in desc_lower for w in ["senior", "lead", "principal", "manager", "head", "sr."]):
            level = "Senior"
            years = 6  # Imputed default
        elif any(w in title_lower or w in desc_lower for w in ["junior", "entry", "intern", "associate", "jr."]):
            level = "Entry"
            years = 1  # Imputed default
        else:
            level = "Unspecified"

    return years, level

def extract_skills(description_text):
    """
    Extracts skill matches from description using regular expressions.
    Returns list of matched skills.
    """
    desc_lower = description_text.lower()
    skills_map = {
        "SQL": r"\bsql\b",
        "Python": r"\bpython\b",
        "Tableau": r"\btableau\b",
        "Power BI": r"\bpower\s*bi\b|\bpbi\b|\bpowerbi\b",
        "Excel": r"\bexcel\b",
        "Machine Learning": r"\bmachine\s*learning\b|\bml\b"
    }

    matched_skills = []
    for skill, pattern in skills_map.items():
        if re.search(pattern, desc_lower):
            matched_skills.append(skill)
            
    return matched_skills

def run_cleaning_pipeline():
    """Runs ETL pipeline to clean staged data and populate core tables."""
    print("=========================================")
    print("      STARTING DATA CLEANING PIPELINE    ")
    print("=========================================")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get unprocessed staging data
    cursor.execute("SELECT id, title, company, location, salary_raw, description_raw FROM staged_jobs WHERE is_processed = 0")
    raw_jobs = cursor.fetchall()
    
    if not raw_jobs:
        print("[ETL] No new raw jobs in staging to clean. Proceeding to export step.")
        conn.close()
        export_dashboard_data()
        return

    print(f"[ETL] Found {len(raw_jobs)} unprocessed raw jobs. Processing...")

    processed_count = 0
    
    for row in raw_jobs:
        staged_id, title, company_raw, location, salary_raw, description = row
        
        # 1. Parse Company Name and Industry
        company_name, industry = parse_company_info(company_raw)
        
        # 2. Parse Salary Range
        sal_min, sal_max, sal_avg = parse_salary(salary_raw)
        
        # 3. Parse Experience
        exp_years, exp_level = parse_experience(description, title)
        
        # 4. Extract Skills
        skills = extract_skills(description)
        
        try:
            # 5. Insert Company (or get ID)
            cursor.execute("INSERT OR IGNORE INTO companies (name, industry) VALUES (?, ?)", (company_name, industry))
            # If already exists, update industry if it was 'Unspecified' before
            if industry != "Unspecified":
                cursor.execute("UPDATE companies SET industry = ? WHERE name = ? AND industry = 'Unspecified'", (industry, company_name))
                
            cursor.execute("SELECT company_id FROM companies WHERE name = ?", (company_name,))
            company_id = cursor.fetchone()[0]
            
            # 6. Insert Job Posting
            cursor.execute("""
                INSERT INTO job_postings (company_id, title, location, salary_min, salary_max, salary_avg, experience_years, experience_level, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (company_id, title, location, sal_min, sal_max, sal_avg, exp_years, exp_level, description))
            
            job_id = cursor.lastrowid
            
            # 7. Insert Skills Required
            for skill in skills:
                cursor.execute("INSERT OR IGNORE INTO skills_required (job_id, skill_name) VALUES (?, ?)", (job_id, skill))
                
            # 8. Mark as processed
            cursor.execute("UPDATE staged_jobs SET is_processed = 1 WHERE id = ?", (staged_id,))
            processed_count += 1
            
        except Exception as e:
            print(f"[Error] Failed to process staged job ID {staged_id}: {e}")
            
    conn.commit()
    conn.close()
    
    print(f"[ETL] Cleaning pipeline complete. Successfully processed {processed_count} jobs.")
    
    # Export metrics for visualization
    export_dashboard_data()
    
    # Trigger machine learning regression training
    try:
        from salary_predictor import train_predictor
        train_predictor()
    except Exception as e:
        print(f"[ETL Warning] Could not train predictor model: {e}")

def export_dashboard_data():
    """Generates structured metrics from SQLite tables and exports to dashboard_data.json."""
    print("[ETL] Exporting metrics for strategic dashboard...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # KPI 1: Total Jobs
    cursor.execute("SELECT COUNT(*) FROM job_postings")
    total_jobs = cursor.fetchone()[0]
    
    # KPI 2: Average Salary
    cursor.execute("SELECT AVG(salary_avg) FROM job_postings WHERE salary_avg IS NOT NULL")
    avg_salary_val = cursor.fetchone()[0]
    avg_salary = int(avg_salary_val) if avg_salary_val else 0
    
    # KPI 3: Skills Frequency
    cursor.execute("""
        SELECT skill_name, COUNT(*) as count 
        FROM skills_required 
        GROUP BY skill_name 
        ORDER BY count DESC
    """)
    skills_counts = [{"skill": row[0], "count": row[1]} for row in cursor.fetchall()]
    
    # Visualizations:
    # 1. BI Tool Demand: Power BI vs Tableau
    power_bi_count = 0
    tableau_count = 0
    for sc in skills_counts:
        if sc["skill"] == "Power BI":
            power_bi_count = sc["count"]
        elif sc["skill"] == "Tableau":
            tableau_count = sc["count"]
            
    bi_tools = {
        "Power BI": power_bi_count,
        "Tableau": tableau_count
    }
    
    # 2. Premium Skills: Average Salary per Skill
    cursor.execute("""
        SELECT sr.skill_name, AVG(jp.salary_avg) as avg_sal, COUNT(jp.job_id) as count
        FROM skills_required sr
        JOIN job_postings jp ON sr.job_id = jp.job_id
        WHERE jp.salary_avg IS NOT NULL
        GROUP BY sr.skill_name
        ORDER BY avg_sal DESC
    """)
    premium_skills = [
        {"skill": row[0], "avg_salary": int(row[1]), "job_count": row[2]}
        for row in cursor.fetchall()
    ]
    
    # 3. Market Concentration: Jobs by Industry
    cursor.execute("""
        SELECT c.industry, COUNT(jp.job_id) as count, AVG(jp.salary_avg) as avg_sal
        FROM job_postings jp
        JOIN companies c ON jp.company_id = c.company_id
        GROUP BY c.industry
        ORDER BY count DESC
    """)
    industries = [
        {"industry": row[0], "job_count": row[1], "avg_salary": int(row[2]) if row[2] else 0}
        for row in cursor.fetchall()
    ]
    
    # 4. Experience vs Salary Distribution
    cursor.execute("""
        SELECT experience_level, COUNT(*), AVG(salary_avg), MIN(salary_min), MAX(salary_max)
        FROM job_postings
        WHERE salary_avg IS NOT NULL
        GROUP BY experience_level
        ORDER BY 
            CASE experience_level 
                WHEN 'Entry' THEN 1 
                WHEN 'Mid' THEN 2 
                WHEN 'Senior' THEN 3 
                ELSE 4 
            END
    """)
    experience_salary = [
        {
            "level": row[0], 
            "count": row[1], 
            "avg_salary": int(row[2]) if row[2] else 0,
            "min_salary": int(row[3]) if row[3] else 0,
            "max_salary": int(row[4]) if row[4] else 0
        }
        for row in cursor.fetchall()
    ]

    # Combine into a single JSON packet
    dashboard_data = {
        "kpis": {
            "total_jobs": total_jobs,
            "average_salary": avg_salary,
            "top_skill": skills_counts[0]["skill"] if skills_counts else "N/A"
        },
        "skills_demand": skills_counts,
        "bi_tools": bi_tools,
        "premium_skills": premium_skills,
        "industries": industries,
        "experience_salary": experience_salary
    }
    
    # Write to file
    os.makedirs(os.path.dirname(DASHBOARD_JSON_PATH), exist_ok=True)
    with open(DASHBOARD_JSON_PATH, 'w') as f:
        json.dump(dashboard_data, f, indent=4)
        
    # Write to JS file for direct local browser opening (bypass CORS)
    js_content = f"const DATA = {json.dumps(dashboard_data, indent=4)};"
    with open(DASHBOARD_JS_PATH, 'w') as f:
        f.write(js_content)
        
    conn.close()
    print(f"[ETL] Metrics successfully written to {DASHBOARD_JSON_PATH} and {DASHBOARD_JS_PATH}")

if __name__ == "__main__":
    run_cleaning_pipeline()
