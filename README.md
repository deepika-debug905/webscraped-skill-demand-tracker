# Market Intelligence: Job Market & Skill Demand Predictor

An end-to-end data engineering and analytics pipeline designed to gather, clean, and visualize regional job market trends for Data Analysts. 

This project demonstrates strong database design, text mining capabilities, automated data crawling robustness, and executive-level business intelligence.

---

## Executive Summary & Architecture

Most portfolio projects use flat static CSVs or generic APIs. This system builds a complete ETL data pipeline:
1. **Mock Data Engine**: A local server serving paginated HTML jobs with varied formatting, text structures, and noise.
2. **Robust Scraper**: Crawls the HTML using custom headers, random sleep intervals, and pagination. Stages raw listings.
3. **Regex ETL Parser**: Parses messy unstructured strings to extract salaries, experience constraints, and technical skills.
4. **Normalized SQL Storage**: Stores elements in a 3NF SQLite database (Companies, Jobs, Skills Required).
5. **Portfolio Dashboard**: A dark-mode, glassmorphic analytics interface rendering interactive Chart.js graphs.
