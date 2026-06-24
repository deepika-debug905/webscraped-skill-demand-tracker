import sqlite3
import os
import re
import json
import time
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "job_market.db")
MODEL_JSON_PATH = os.path.join(BASE_DIR, "database", "salary_model.json")
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")

# Initialize FastAPI
app = FastAPI(
    title="Market Intelligence API",
    description="Backend API serving the Job Market & Skill Demand Predictor",
    version="1.0.0"
)

# CORS Configuration (To allow local file testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_database_if_missing():
    if not os.path.exists(DB_PATH):
        print("[API] Database not found. Initializing empty database from schema...")
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        schema_path = os.path.join(BASE_DIR, "database", "schema.sql")
        if os.path.exists(schema_path):
            try:
                with open(schema_path, 'r') as f:
                    cursor.executescript(f.read())
                conn.commit()
                print("[API] Database schema applied successfully.")
            except Exception as e:
                print(f"[API Error] Failed to apply schema: {e}")
        else:
            print("[API Warning] schema.sql not found. Database cannot be initialized.")
        conn.close()

# Auto-initialize database on server import/start
init_database_if_missing()

# Helper function to get database connection
def get_db_connection(read_only: bool = False):
    if not os.path.exists(DB_PATH):
        init_database_if_missing()
        
    if not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=503, 
            detail="Database file could not be created."
        )
        
    if read_only:
        # Connect in read-only mode using URI
        db_uri = f"file:{DB_PATH}?mode=ro"
        return sqlite3.connect(db_uri, uri=True)
    else:
        return sqlite3.connect(DB_PATH)

# Helper to load trained ML model weights
def load_model_weights():
    default_weights = {
        "intercept": 62500.0,
        "experience_year_value": 4800.0,
        "SQL": 6500.0,
        "Python": 9200.0,
        "Tableau": 5800.0,
        "Power BI": 7800.0,
        "Excel": 2500.0,
        "Machine Learning": 14500.0
    }
    if os.path.exists(MODEL_JSON_PATH):
        try:
            with open(MODEL_JSON_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            return default_weights
    return default_weights

# Pydantic schema for Resume Prediction
class ResumePayload(BaseModel):
    resume_text: str
    experience_years: int

# Pydantic schema for SQL execution
class SQLQueryPayload(BaseModel):
    query: str

# --- API Endpoints ---

@app.get("/api/meta")
def get_meta():
    """Returns metadata about the database, like available locations, industries, and last scrape time."""
    try:
        conn = get_db_connection(read_only=True)
        cursor = conn.cursor()
        
        # Get locations
        cursor.execute("SELECT DISTINCT location FROM job_postings ORDER BY location")
        locations = [row[0] for row in cursor.fetchall()]
        
        # Get industries
        cursor.execute("SELECT DISTINCT industry FROM companies ORDER BY industry")
        industries = [row[0] for row in cursor.fetchall()]
        
        # Get last scraped time
        cursor.execute("SELECT MAX(scraped_at) FROM staged_jobs")
        last_scraped = cursor.fetchone()[0]
        
        conn.close()
        return {
            "locations": locations,
            "industries": industries,
            "last_scraped": last_scraped
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs")
def get_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = "",
    location: Optional[str] = "",
    skill: Optional[str] = "",
    experience_level: Optional[str] = ""
):
    """Returns a paginated list of job postings, with search and multi-criteria filters."""
    try:
        conn = get_db_connection(read_only=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            FROM job_postings j
            JOIN companies c ON j.company_id = c.company_id
        """
        conditions = []
        params = {}
        
        if search:
            conditions.append("(j.title LIKE :search OR j.description LIKE :search OR c.name LIKE :search)")
            params["search"] = f"%{search}%"
        if location:
            conditions.append("j.location = :location")
            params["location"] = location
        if experience_level:
            conditions.append("j.experience_level = :experience_level")
            params["experience_level"] = experience_level
        if skill:
            conditions.append("j.job_id IN (SELECT job_id FROM skills_required WHERE skill_name = :skill)")
            params["skill"] = skill
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        # Count total records matching filters
        count_cursor = conn.cursor()
        count_cursor.execute(f"SELECT COUNT(*) {query}", params)
        total_records = count_cursor.fetchone()[0]
        
        # Select actual page of records
        select_query = f"""
            SELECT j.job_id, j.title, j.location, j.salary_min, j.salary_max, j.salary_avg, 
                   j.experience_years, j.experience_level, j.description, j.posted_date,
                   c.name as company_name, c.industry
            {query}
            ORDER BY j.job_id DESC
            LIMIT :limit OFFSET :offset
        """
        params["limit"] = limit
        params["offset"] = (page - 1) * limit
        
        cursor.execute(select_query, params)
        rows = cursor.fetchall()
        
        jobs = []
        for r in rows:
            job_dict = dict(r)
            
            # Fetch skills for this job
            skills_cursor = conn.cursor()
            skills_cursor.execute("SELECT skill_name FROM skills_required WHERE job_id = ?", (job_dict["job_id"],))
            job_dict["skills"] = [row[0] for row in skills_cursor.fetchall()]
            
            jobs.append(job_dict)
            
        conn.close()
        
        total_pages = (total_records + limit - 1) // limit
        return {
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "jobs": jobs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics")
def get_analytics(
    industry: Optional[str] = None,
    location: Optional[str] = None
):
    """Returns analytics data (KPIs, Chart datasets) matching optional filters."""
    try:
        conn = get_db_connection(read_only=True)
        cursor = conn.cursor()
        
        # Build filter conditions
        where_clauses = []
        params = {}
        if industry:
            where_clauses.append("c.industry = :industry")
            params["industry"] = industry
        if location:
            where_clauses.append("j.location = :location")
            params["location"] = location
            
        where_str = ""
        if where_clauses:
            where_str = "WHERE " + " AND ".join(where_clauses)
            
        # 1. KPIs
        cursor.execute(f"""
            SELECT COUNT(j.job_id), AVG(j.salary_avg)
            FROM job_postings j
            JOIN companies c ON j.company_id = c.company_id
            {where_str}
        """, params)
        total_jobs, avg_salary_val = cursor.fetchone()
        avg_salary = int(avg_salary_val) if avg_salary_val else 0
        
        # 2. Skills demand count
        cursor.execute(f"""
            SELECT sr.skill_name, COUNT(*) as count
            FROM skills_required sr
            JOIN job_postings j ON sr.job_id = j.job_id
            JOIN companies c ON j.company_id = c.company_id
            {where_str}
            GROUP BY sr.skill_name
            ORDER BY count DESC
        """, params)
        skills_counts = [{"skill": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        top_skill = skills_counts[0]["skill"] if skills_counts else "N/A"
        
        # 3. BI tools comparison
        power_bi_count = next((s["count"] for s in skills_counts if s["skill"] == "Power BI"), 0)
        tableau_count = next((s["count"] for s in skills_counts if s["skill"] == "Tableau"), 0)
        bi_tools = {
            "Power BI": power_bi_count,
            "Tableau": tableau_count
        }
        
        # 4. Premium skills average salaries
        where_salary_str = "WHERE j.salary_avg IS NOT NULL"
        if where_clauses:
            where_salary_str = "WHERE " + " AND ".join(where_clauses) + " AND j.salary_avg IS NOT NULL"
            
        cursor.execute(f"""
            SELECT sr.skill_name, AVG(j.salary_avg) as avg_sal, COUNT(j.job_id) as count
            FROM skills_required sr
            JOIN job_postings j ON sr.job_id = j.job_id
            JOIN companies c ON j.company_id = c.company_id
            {where_salary_str}
            GROUP BY sr.skill_name
            ORDER BY avg_sal DESC
        """, params)
        premium_skills = [
            {"skill": row[0], "avg_salary": int(row[1]), "job_count": row[2]}
            for row in cursor.fetchall()
        ]
        
        # 5. Industry distribution
        cursor.execute(f"""
            SELECT c.industry, COUNT(j.job_id) as count, AVG(j.salary_avg) as avg_sal
            FROM job_postings j
            JOIN companies c ON j.company_id = c.company_id
            {where_str}
            GROUP BY c.industry
            ORDER BY count DESC
        """, params)
        industries = [
            {"industry": row[0], "job_count": row[1], "avg_salary": int(row[2]) if row[2] else 0}
            for row in cursor.fetchall()
        ]
        
        # 6. Experience vs salary distribution
        cursor.execute(f"""
            SELECT j.experience_level, COUNT(*), AVG(j.salary_avg), MIN(j.salary_min), MAX(j.salary_max)
            FROM job_postings j
            JOIN companies c ON j.company_id = c.company_id
            {where_salary_str}
            GROUP BY j.experience_level
            ORDER BY 
                CASE j.experience_level 
                    WHEN 'Entry' THEN 1 
                    WHEN 'Mid' THEN 2 
                    WHEN 'Senior' THEN 3 
                    ELSE 4 
                END
        """, params)
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
        
        conn.close()
        
        return {
            "kpis": {
                "total_jobs": total_jobs,
                "average_salary": avg_salary,
                "top_skill": top_skill
            },
            "skills_demand": skills_counts,
            "bi_tools": bi_tools,
            "premium_skills": premium_skills,
            "industries": industries,
            "experience_salary": experience_salary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/skills-correlation")
def get_skills_correlation(
    industry: Optional[str] = None,
    location: Optional[str] = None
):
    """Calculates skill co-occurrence count to understand which skills are requested together."""
    try:
        conn = get_db_connection(read_only=True)
        cursor = conn.cursor()
        
        where_clauses = []
        params = {}
        if industry:
            where_clauses.append("c.industry = :industry")
            params["industry"] = industry
        if location:
            where_clauses.append("j.location = :location")
            params["location"] = location
            
        where_str = ""
        if where_clauses:
            where_str = "WHERE " + " AND ".join(where_clauses)
            
        cursor.execute(f"""
            SELECT s1.skill_name as skill_a, s2.skill_name as skill_b, COUNT(*) as count
            FROM skills_required s1
            JOIN skills_required s2 ON s1.job_id = s2.job_id AND s1.skill_name < s2.skill_name
            JOIN job_postings j ON s1.job_id = j.job_id
            JOIN companies c ON j.company_id = c.company_id
            {where_str}
            GROUP BY s1.skill_name, s2.skill_name
            ORDER BY count DESC
        """, params)
        
        cooccurrence = [
            {"skill_a": row[0], "skill_b": row[1], "count": row[2]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return cooccurrence
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/predict-salary")
def predict_salary(payload: ResumePayload):
    """Predicts salary and analyzes skill gap based on resume text and experience."""
    weights = load_model_weights()
    
    resume_lower = payload.resume_text.lower()
    
    skills_regex = {
        "SQL": r"\bsql\b",
        "Python": r"\bpython\b",
        "Tableau": r"\btableau\b",
        "Power BI": r"\bpower\s*bi\b|\bpbi\b|\bpowerbi\b",
        "Excel": r"\bexcel\b",
        "Machine Learning": r"\bmachine\s*learning\b|\bml\b"
    }
    
    match_count = 0
    skill_matches = {}
    
    for skill, pattern in skills_regex.items():
        has_skill = bool(re.search(pattern, resume_lower))
        skill_matches[skill] = has_skill
        if has_skill:
            match_count += 1
            
    match_percent = int((match_count / len(skills_regex)) * 100)
    
    # Calculate salary
    estimated_salary = weights.get("intercept", 62500.0)
    estimated_salary += weights.get("experience_year_value", 4800.0) * payload.experience_years
    
    for skill, matched in skill_matches.items():
        if matched:
            estimated_salary += weights.get(skill, 0)
            
    # Skill breakdown
    skill_breakdown = []
    for skill in skills_regex.keys():
        skill_breakdown.append({
            "skill": skill,
            "matched": skill_matches[skill],
            "value_addition": weights.get(skill, 0)
        })
        
    # Sort skills: matched first, then missing skills sorted by value addition
    skill_breakdown.sort(key=lambda x: (not x["matched"], -x["value_addition"]))
    
    return {
        "match_percent": match_percent,
        "estimated_salary": round(estimated_salary, 2),
        "skills_analysis": skill_breakdown,
        "experience_years": payload.experience_years
    }

@app.post("/api/sql/query")
def run_sql_query(payload: SQLQueryPayload):
    """Runs custom analytical SQL SELECT queries securely in read-only mode."""
    # 1. Clean query
    raw_query = payload.query.strip()
    
    # Remove single line comments
    clean_query = re.sub(r'--.*$', '', raw_query, flags=re.MULTILINE)
    # Remove block comments
    clean_query = re.sub(r'/\*.*?\*/', '', clean_query, flags=re.DOTALL)
    clean_query = clean_query.strip()
    
    if not clean_query:
        raise HTTPException(status_code=400, detail="Query is empty.")
        
    # 2. Strict read-only syntax check
    query_lower = clean_query.lower()
    if not (query_lower.startswith("select") or query_lower.startswith("with")):
        raise HTTPException(
            status_code=400, 
            detail="Security Block: Only SELECT or WITH queries are allowed on this analytical sandbox."
        )
        
    # Check for forbidden syntax words
    forbidden = ["insert", "update", "delete", "drop", "create", "alter", "replace", 
                 "truncate", "grant", "revoke", "pragma", "vacuum", "attach", "detach"]
                 
    for keyword in forbidden:
        if re.search(r'\b' + keyword + r'\b', query_lower):
            raise HTTPException(
                status_code=400, 
                detail=f"Security Block: Keyword '{keyword}' is blocked in this read-only sandbox."
            )
            
    # 3. Execution in read-only connection
    try:
        conn = get_db_connection(read_only=True)
        cursor = conn.cursor()
        
        start_time = time.perf_counter()
        cursor.execute(clean_query)
        rows = cursor.fetchall()
        end_time = time.perf_counter()
        
        # Get column names
        columns = [description[0] for description in cursor.description] if cursor.description else []
        
        # Transform rows to dictionaries
        results = []
        for row in rows:
            results.append({columns[i]: row[i] for i in range(len(columns))})
            
        conn.close()
        
        return {
            "success": True,
            "elapsed_ms": round((end_time - start_time) * 1000, 2),
            "columns": columns,
            "row_count": len(results),
            "data": results[:500] # Limit to 500 records to prevent browser crash
        }
        
    except sqlite3.OperationalError as e:
        # Catch SQL syntax errors and read-only violation errors
        return {
            "success": False,
            "error": f"SQLite Error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error: {str(e)}"
        }

# Mount the static files from the dashboard directory at root "/"
# StaticFiles will serve index.html at "/", app.js at "/app.js", etc.
app.mount("/", StaticFiles(directory=DASHBOARD_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    import sys
    # Add scripts folder to path so uvicorn can find the module when run directly
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
        
    print("[API] Starting API Server on http://localhost:8000...")
    uvicorn.run("api_server:app", host="127.0.0.1", port=8000, reload=True)
