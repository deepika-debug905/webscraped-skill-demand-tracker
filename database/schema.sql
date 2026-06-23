-- ==========================================
-- Job Market & Skill Demand Predictor
-- Database Relational Schema (3NF)
-- Compatible with SQLite, PostgreSQL, and MySQL
-- ==========================================

-- Drop tables if they exist (for easy re-running)
DROP TABLE IF EXISTS skills_required;
DROP TABLE IF EXISTS job_postings;
DROP TABLE IF EXISTS companies;
DROP TABLE IF EXISTS staged_jobs;

-- 1. Staging Table: Staged Jobs (Staging layer for raw crawled data)
CREATE TABLE staged_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT NOT NULL,
    salary_raw TEXT,
    description_raw TEXT NOT NULL,
    scraped_at TEXT DEFAULT CURRENT_TIMESTAMP,
    is_processed INTEGER DEFAULT 0 -- 0 = Pending cleaning, 1 = Cleaned & Transformed
);

-- 2. Dimension Table: Companies
CREATE TABLE companies (
    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    industry TEXT NOT NULL
);

-- 3. Fact Table: Job Postings
CREATE TABLE job_postings (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    location TEXT NOT NULL,
    salary_min REAL,
    salary_max REAL,
    salary_avg REAL,
    experience_years INTEGER,
    experience_level TEXT NOT NULL CHECK(experience_level IN ('Entry', 'Mid', 'Senior', 'Unspecified')),
    description TEXT NOT NULL,
    posted_date TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE RESTRICT
);

-- 4. Bridge Table: Skills Required (Many-to-Many relationship between Job Postings and Skills)
CREATE TABLE skills_required (
    job_id INTEGER NOT NULL,
    skill_name TEXT NOT NULL,
    PRIMARY KEY (job_id, skill_name),
    FOREIGN KEY (job_id) REFERENCES job_postings(job_id) ON DELETE CASCADE
);

-- Create Indexes to Optimize Query Performance
CREATE INDEX idx_job_postings_company_id ON job_postings(company_id);
CREATE INDEX idx_job_postings_salary_avg ON job_postings(salary_avg);
CREATE INDEX idx_skills_required_name ON skills_required(skill_name);
CREATE INDEX idx_staged_jobs_processed ON staged_jobs(is_processed);
