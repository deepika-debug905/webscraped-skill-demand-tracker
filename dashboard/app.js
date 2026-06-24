// ==================================================
// Job Market & Skill Demand Predictor
// Dashboard Front-End Application Code
// ==================================================

// Determine API Base URL (Allows local file protocol to connect to localhost)
const API_BASE = window.location.protocol === "file:" ? "http://localhost:8000" : "";

// Fallback weights for ML Estimation if backend API is offline
const FALLBACK_MODEL_WEIGHTS = {
    "intercept": 62500.0,
    "experience_year_value": 4800.0,
    "SQL": 6500.0,
    "Python": 9200.0,
    "Tableau": 5800.0,
    "Power BI": 7800.0,
    "Excel": 2500.0,
    "Machine Learning": 14500.0
};

// Fallback demo data if SQLite database has not been compiled
const DEMO_DATA = {
    "kpis": {
        "total_jobs": 142,
        "average_salary": 98450,
        "top_skill": "SQL"
    },
    "skills_demand": [
        { "skill": "SQL", "count": 108 },
        { "skill": "Python", "count": 78 },
        { "skill": "Excel", "count": 72 },
        { "skill": "Power BI", "count": 65 },
        { "skill": "Tableau", "count": 52 },
        { "skill": "Machine Learning", "count": 32 }
    ],
    "bi_tools": {
        "Power BI": 65,
        "Tableau": 52
    },
    "premium_skills": [
        { "skill": "Machine Learning", "avg_salary": 121000, "job_count": 32 },
        { "skill": "Python", "avg_salary": 106500, "job_count": 78 },
        { "skill": "SQL", "avg_salary": 99200, "job_count": 108 },
        { "skill": "Power BI", "avg_salary": 96800, "job_count": 65 },
        { "skill": "Tableau", "avg_salary": 94100, "job_count": 52 },
        { "skill": "Excel", "avg_salary": 72400, "job_count": 72 }
    ],
    "industries": [
        { "industry": "Tech", "job_count": 48, "avg_salary": 108000 },
        { "industry": "Finance", "job_count": 38, "avg_salary": 102000 },
        { "industry": "Healthcare", "job_count": 28, "avg_salary": 91500 },
        { "industry": "Logistics", "job_count": 18, "avg_salary": 87000 },
        { "industry": "Energy", "job_count": 10, "avg_salary": 94000 }
    ],
    "experience_salary": [
        { "level": "Entry", "count": 42, "avg_salary": 72500, "min_salary": 50000, "max_salary": 90000 },
        { "level": "Mid", "count": 68, "avg_salary": 99400, "min_salary": 80000, "max_salary": 125000 },
        { "level": "Senior", "count": 32, "avg_salary": 136200, "min_salary": 110000, "max_salary": 170000 }
    ]
};

// Global variables
let isLiveAPI = false;
let activeAnalyticsData = DEMO_DATA;
let activeCharts = {};
let lastSQLResults = null;

// Jobs Explorer pagination states
let jobsCurrentPage = 1;
const jobsLimit = 6;
let jobsTotalPages = 1;

// Global Chart configurations
Chart.defaults.color = '#9ca3af';
Chart.defaults.font.family = "'Outfit', sans-serif";
Chart.defaults.font.size = 11;

document.addEventListener("DOMContentLoaded", async () => {
    // 1. Check API server connectivity
    await checkApiStatus();

    // 2. Initialize Navigation tabs
    initNavigation();

    // 3. Initialize Filters & Load Initial Analytics
    await initAnalyticsDashboard();

    // 4. Initialize Job Explorer listeners
    initJobExplorer();

    // 5. Initialize SQL Playground
    initSQLPlayground();

    // 6. Initialize Resume Predictor
    initResumePredictor();
});

// Check if FastAPI is running
async function checkApiStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/meta`);
        if (response.ok) {
            isLiveAPI = true;
            console.log("[App] Successfully connected to live FastAPI backend database!");
            document.getElementById("no-data-alert").style.display = "none";
        } else {
            throw new Error("Meta status check failed");
        }
    } catch (e) {
        isLiveAPI = false;
        console.warn("[App] API server offline. Falling back to local offline sandbox mode.");
        document.getElementById("no-data-alert").style.display = "block";
    }
}

// Navigation Tab Management
function initNavigation() {
    const tabs = document.querySelectorAll(".tab-btn");
    tabs.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            
            // Toggle active buttons
            tabs.forEach(t => t.classList.remove("active"));
            btn.classList.add("active");
            
            // Toggle views
            document.querySelectorAll(".tab-view").forEach(view => {
                view.style.display = "none";
            });
            
            if (targetTab === "dashboard") {
                document.getElementById("view-dashboard").style.display = "block";
            } else if (targetTab === "explorer") {
                document.getElementById("view-explorer").style.display = "block";
                loadJobsExplorer();
            } else if (targetTab === "sql") {
                document.getElementById("view-sql").style.display = "block";
            } else if (targetTab === "ml") {
                document.getElementById("view-ml").style.display = "block";
            }
        });
    });
}

// ==================================================
// VIEW 1: ANALYTICS DASHBOARD
// ==================================================
async function initAnalyticsDashboard() {
    const indSelect = document.getElementById("dashboard-filter-industry");
    const locSelect = document.getElementById("dashboard-filter-location");
    const btnClear = document.getElementById("btn-clear-filters");

    if (isLiveAPI) {
        try {
            // Load dropdown lists from metadata
            const response = await fetch(`${API_BASE}/api/meta`);
            const meta = await response.json();

            meta.industries.forEach(ind => {
                if(ind && ind !== "Unspecified") {
                    const opt = document.createElement("option");
                    opt.value = ind;
                    opt.textContent = ind;
                    indSelect.appendChild(opt);
                }
            });

            meta.locations.forEach(loc => {
                if(loc) {
                    const opt = document.createElement("option");
                    opt.value = loc;
                    opt.textContent = loc;
                    locSelect.appendChild(opt);
                }
            });
        } catch (e) {
            console.error("Error loading filter dropdowns:", e);
        }
    } else {
        // Fallback dropdown items from DEMO_DATA
        const industries = [...new Set(DEMO_DATA.industries.map(i => i.industry))];
        industries.forEach(ind => {
            const opt = document.createElement("option");
            opt.value = ind;
            opt.textContent = ind;
            indSelect.appendChild(opt);
        });
    }

    // Set change listeners
    indSelect.addEventListener("change", updateAnalyticsData);
    locSelect.addEventListener("change", updateAnalyticsData);
    
    btnClear.addEventListener("click", () => {
        indSelect.value = "";
        locSelect.value = "";
        updateAnalyticsData();
    });

    // Initial load
    await updateAnalyticsData();
}

async function updateAnalyticsData() {
    const industry = document.getElementById("dashboard-filter-industry").value;
    const location = document.getElementById("dashboard-filter-location").value;

    if (isLiveAPI) {
        try {
            let url = `${API_BASE}/api/analytics?`;
            if (industry) url += `industry=${encodeURIComponent(industry)}&`;
            if (location) url += `location=${encodeURIComponent(location)}&`;

            const response = await fetch(url);
            activeAnalyticsData = await response.json();
        } catch (e) {
            console.error("Error fetching filtered analytics:", e);
            activeAnalyticsData = DEMO_DATA;
        }
    } else {
        // Perform frontend client-side filtering on DEMO_DATA to keep it interactive
        activeAnalyticsData = filterDemoData(industry, location);
    }

    // Populate KPIs
    document.getElementById("kpi-total-jobs").textContent = activeAnalyticsData.kpis.total_jobs;
    document.getElementById("kpi-avg-salary").textContent = activeAnalyticsData.kpis.total_jobs > 0 
        ? "$" + activeAnalyticsData.kpis.average_salary.toLocaleString()
        : "$0";
    document.getElementById("kpi-top-skill").textContent = activeAnalyticsData.kpis.top_skill;

    // Render Charts
    renderBIPositioning(activeAnalyticsData.bi_tools);
    renderPremiumSkills(activeAnalyticsData.premium_skills);
    renderIndustries(activeAnalyticsData.industries);
    renderCareerVelocity(activeAnalyticsData.experience_salary);
}

// Client-side filtering simulation for offline fallback
function filterDemoData(industry, location) {
    // Return base DEMO_DATA if no filters
    if (!industry && !location) return DEMO_DATA;

    // Simple mockup filtering coefficients
    let factor = 1.0;
    if (industry === "Tech") factor = 1.15;
    else if (industry === "Finance") factor = 1.08;
    else if (industry === "Logistics") factor = 0.88;
    else if (industry === "Healthcare") factor = 0.94;
    else if (industry === "Energy") factor = 0.97;

    if (location) factor *= 0.95; // slight discount for single locations

    const totalJobs = Math.max(5, Math.round(DEMO_DATA.kpis.total_jobs * (factor / 2.5)));
    const avgSalary = Math.round(DEMO_DATA.kpis.average_salary * factor);
    
    const filteredSkills = DEMO_DATA.skills_demand.map(s => ({
        ...s,
        count: Math.max(1, Math.round(s.count * (factor / 2.5)))
    })).sort((a,b) => b.count - a.count);

    const filteredPremium = DEMO_DATA.premium_skills.map(s => ({
        ...s,
        avg_salary: Math.round(s.avg_salary * factor),
        job_count: Math.max(1, Math.round(s.job_count * (factor / 2.5)))
    })).sort((a,b) => b.avg_salary - a.avg_salary);

    const filteredIndustries = DEMO_DATA.industries.filter(i => !industry || i.industry === industry).map(i => ({
        ...i,
        job_count: Math.max(1, Math.round(i.job_count * (location ? 0.7 : 1.0))),
        avg_salary: Math.round(i.avg_salary * factor)
    }));

    const filteredExp = DEMO_DATA.experience_salary.map(e => ({
        ...e,
        avg_salary: Math.round(e.avg_salary * factor),
        min_salary: Math.round(e.min_salary * factor),
        max_salary: Math.round(e.max_salary * factor),
        count: Math.max(1, Math.round(e.count * (factor / 2.5)))
    }));

    const pbCount = Math.round(totalJobs * 0.45);
    const tabCount = Math.round(totalJobs * 0.38);

    return {
        "kpis": {
            "total_jobs": totalJobs,
            "average_salary": avgSalary,
            "top_skill": filteredSkills[0] ? filteredSkills[0].skill : "N/A"
        },
        "skills_demand": filteredSkills,
        "bi_tools": {
            "Power BI": pbCount,
            "Tableau": tabCount
        },
        "premium_skills": filteredPremium,
        "industries": filteredIndustries,
        "experience_salary": filteredExp
    };
}

// Chart Renderers (Destroy existing chart instances first to avoid Canvas overlaps)
function renderBIPositioning(biData) {
    if (activeCharts.bi) activeCharts.bi.destroy();
    
    const ctx = document.getElementById("chart-bi-battle").getContext("2d");
    const pbCount = biData["Power BI"] || 0;
    const tabCount = biData["Tableau"] || 0;
    const total = pbCount + tabCount;

    activeCharts.bi = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: [`Power BI (${pbCount})`, `Tableau (${tabCount})`],
            datasets: [{
                data: [pbCount, tabCount],
                backgroundColor: ['#f59e0b', '#3b82f6'],
                borderColor: '#141a2e',
                borderWidth: 2,
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { padding: 15, font: { weight: '500' } }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const val = context.raw;
                            const pct = total > 0 ? Math.round((val / total) * 100) : 0;
                            return ` ${context.label.split(' (')[0]}: ${val} (${pct}%)`;
                        }
                    }
                }
            },
            cutout: '72%'
        }
    });
}

function renderPremiumSkills(skillsData) {
    if (activeCharts.premium) activeCharts.premium.destroy();

    const ctx = document.getElementById("chart-premium-skills").getContext("2d");
    const labels = skillsData.map(item => item.skill);
    const salaries = skillsData.map(item => item.avg_salary);
    const counts = skillsData.map(item => item.job_count);

    activeCharts.premium = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Annual Salary',
                data: salaries,
                backgroundColor: 'rgba(139, 92, 246, 0.65)',
                borderColor: '#8b5cf6',
                borderWidth: 1.5,
                borderRadius: 5,
                hoverBackgroundColor: '#8b5cf6',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { callback: value => '$' + (value / 1000) + 'k' }
                },
                x: { grid: { display: false } }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const idx = context.dataIndex;
                            return ` Salary: $${context.raw.toLocaleString()} | Mentions: ${counts[idx]}`;
                        }
                    }
                }
            }
        }
    });
}

function renderIndustries(industryData) {
    if (activeCharts.industries) activeCharts.industries.destroy();

    const ctx = document.getElementById("chart-industries").getContext("2d");
    const labels = industryData.map(item => item.industry);
    const counts = industryData.map(item => item.job_count);
    const salaries = industryData.map(item => item.avg_salary);

    activeCharts.industries = new Chart(ctx, {
        type: 'bar',
        indexAxis: 'y',
        data: {
            labels: labels,
            datasets: [{
                label: 'Openings Scraped',
                data: counts,
                backgroundColor: 'rgba(16, 185, 129, 0.65)',
                borderColor: '#10b981',
                borderWidth: 1.5,
                borderRadius: 5,
                hoverBackgroundColor: '#10b981',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { precision: 0 }
                },
                y: { grid: { display: false } }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const idx = context.dataIndex;
                            return ` Openings: ${context.raw} | Avg Salary: $${salaries[idx].toLocaleString()}`;
                        }
                    }
                }
            }
        }
    });
}

function renderCareerVelocity(expData) {
    if (activeCharts.velocity) activeCharts.velocity.destroy();

    const ctx = document.getElementById("chart-experience-salary").getContext("2d");
    const labels = expData.map(item => item.level);
    const averages = expData.map(item => item.avg_salary);
    const mins = expData.map(item => item.min_salary);
    const maxs = expData.map(item => item.max_salary);

    activeCharts.velocity = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Max Salary Bound',
                    data: maxs,
                    borderColor: 'rgba(239, 68, 68, 0.5)',
                    backgroundColor: 'transparent',
                    borderDash: [4, 4],
                    pointBackgroundColor: '#ef4444',
                    borderWidth: 1.5,
                    tension: 0.15
                },
                {
                    label: 'Average Rate',
                    data: averages,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.08)',
                    pointBackgroundColor: '#3b82f6',
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    borderWidth: 3.5,
                    fill: true,
                    tension: 0.15
                },
                {
                    label: 'Min Salary Bound',
                    data: mins,
                    borderColor: 'rgba(16, 185, 129, 0.5)',
                    backgroundColor: 'transparent',
                    borderDash: [4, 4],
                    pointBackgroundColor: '#10b981',
                    borderWidth: 1.5,
                    tension: 0.15
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { callback: value => '$' + (value / 1000) + 'k' }
                },
                x: { grid: { display: false } }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 10, padding: 12 }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return ` ${context.dataset.label}: $${context.raw.toLocaleString()}`;
                        }
                    }
                }
            }
        }
    });
}

// ==================================================
// VIEW 2: JOB EXPLORER
// ==================================================
let cachedLocations = [];

async function initJobExplorer() {
    const searchInput = document.getElementById("job-search-input");
    const locSelect = document.getElementById("job-filter-location");
    const skillSelect = document.getElementById("job-filter-skill");
    const expSelect = document.getElementById("job-filter-experience");

    // Connect to listeners
    searchInput.addEventListener("input", debounce(() => {
        jobsCurrentPage = 1;
        loadJobsExplorer();
    }, 300));

    locSelect.addEventListener("change", () => {
        jobsCurrentPage = 1;
        loadJobsExplorer();
    });

    skillSelect.addEventListener("change", () => {
        jobsCurrentPage = 1;
        loadJobsExplorer();
    });

    expSelect.addEventListener("change", () => {
        jobsCurrentPage = 1;
        loadJobsExplorer();
    });
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

async function loadJobsExplorer() {
    const searchVal = document.getElementById("job-search-input").value;
    const locationVal = document.getElementById("job-filter-location").value;
    const skillVal = document.getElementById("job-filter-skill").value;
    const expVal = document.getElementById("job-filter-experience").value;

    const listContainer = document.getElementById("jobs-list-container");
    const paginationInfo = document.getElementById("jobs-pagination-info");
    const paginationButtons = document.getElementById("jobs-pagination-buttons");
    const locSelect = document.getElementById("job-filter-location");

    // If live API, pull filtered paginated jobs
    if (isLiveAPI) {
        try {
            // Lazy load unique locations for Job Explorer dropdown
            if (cachedLocations.length === 0) {
                const metaResponse = await fetch(`${API_BASE}/api/meta`);
                const meta = await metaResponse.json();
                cachedLocations = meta.locations;
                cachedLocations.forEach(loc => {
                    if (loc) {
                        const opt = document.createElement("option");
                        opt.value = loc;
                        opt.textContent = loc;
                        locSelect.appendChild(opt);
                    }
                });
            }

            let url = `${API_BASE}/api/jobs?page=${jobsCurrentPage}&limit=${jobsLimit}`;
            if (searchVal) url += `&search=${encodeURIComponent(searchVal)}`;
            if (locationVal) url += `&location=${encodeURIComponent(locationVal)}`;
            if (skillVal) url += `&skill=${encodeURIComponent(skillVal)}`;
            if (expVal) url += `&experience_level=${encodeURIComponent(expVal)}`;

            listContainer.innerHTML = `<div style="text-align:center; padding:40px; color:var(--text-secondary)">Loading matching jobs...</div>`;

            const response = await fetch(url);
            const data = await response.json();

            jobsTotalPages = data.total_pages;

            if (data.jobs.length === 0) {
                listContainer.innerHTML = `<div style="text-align:center; padding:40px; color:var(--text-secondary)">No job postings found matching selected criteria.</div>`;
                paginationInfo.textContent = "Showing 0 of 0 jobs";
                paginationButtons.innerHTML = "";
                document.getElementById("job-detail-panel").innerHTML = `<div style="color: var(--text-secondary); text-align: center; padding: 40px 0;"><p>No job selected.</p></div>`;
                return;
            }

            renderJobsList(data.jobs);
            paginationInfo.textContent = `Showing ${((jobsCurrentPage - 1) * jobsLimit) + 1} - ${Math.min(jobsCurrentPage * jobsLimit, data.total_records)} of ${data.total_records} jobs`;
            renderPaginationControls(jobsCurrentPage, jobsTotalPages);

            // Auto-select first job details
            showJobDetails(data.jobs[0]);

        } catch (e) {
            console.error("Error loading job explorer jobs:", e);
            listContainer.innerHTML = `<div style="color:#ef4444; text-align:center; padding:20px">Error loading database listings. Please start the server.</div>`;
        }
    } else {
        // Mock offline job search
        listContainer.innerHTML = `<div style="text-align:center; padding:40px; color:var(--text-secondary)">Offline Mode: Job database query requires FastAPI backend connection.</div>`;
        paginationInfo.textContent = "Showing 0 of 0 jobs";
        paginationButtons.innerHTML = "";
    }
}

function renderJobsList(jobs) {
    const listContainer = document.getElementById("jobs-list-container");
    listContainer.innerHTML = "";

    jobs.forEach((job, idx) => {
        const card = document.createElement("div");
        card.className = "job-item-card" + (idx === 0 ? " active" : "");
        card.setAttribute("data-id", job.job_id);

        const heading = document.createElement("div");
        heading.className = "job-item-header";
        
        const titleSec = document.createElement("div");
        titleSec.innerHTML = `
            <h4 class="job-item-title">${job.title}</h4>
            <div class="job-item-company">${job.company_name}</div>
        `;
        heading.appendChild(titleSec);

        const salVal = (job.salary_min && job.salary_max) 
            ? `$${Math.round(job.salary_min / 1000)}k - $${Math.round(job.salary_max / 1000)}k`
            : "Competitive";
        
        const salSpan = document.createElement("span");
        salSpan.className = "job-item-salary";
        salSpan.textContent = salVal;
        heading.appendChild(salSpan);

        card.appendChild(heading);

        const meta = document.createElement("div");
        meta.className = "job-item-meta";
        meta.innerHTML = `
            <span>📍 ${job.location}</span>
            <span>💼 ${job.experience_level} Level (${job.experience_years ? job.experience_years + ' yrs' : 'Unspecified'})</span>
            <span>🏢 ${job.industry}</span>
        `;
        card.appendChild(meta);

        // Skill tags
        const skillsDiv = document.createElement("div");
        skillsDiv.className = "job-item-skills";
        
        // Grab skills already detected on this job
        const jobSkills = job.skills || [];
        
        // Get currently analyzed skills from Resume Matcher (if run)
        const matchedResumeSkills = getMatchedResumeSkills();
        
        jobSkills.forEach(s => {
            const sb = document.createElement("span");
            const isMatched = matchedResumeSkills.includes(s.toLowerCase());
            sb.className = "skill-badge" + (isMatched ? " matched" : "");
            sb.textContent = s;
            skillsDiv.appendChild(sb);
        });
        card.appendChild(skillsDiv);

        // Click event to show details
        card.addEventListener("click", () => {
            document.querySelectorAll(".job-item-card").forEach(c => c.classList.remove("active"));
            card.classList.add("active");
            showJobDetails(job);
        });

        listContainer.appendChild(card);
    });
}

function getMatchedResumeSkills() {
    const resumeText = (document.getElementById("resume-input").value || "").toLowerCase();
    const skillsRegex = {
        "sql": /\bsql\b/,
        "python": /\bpython\b/,
        "tableau": /\btableau\b/,
        "power bi": /\bpower\s*bi\b|\bpbi\b|\bpowerbi\b/,
        "excel": /\bexcel\b/,
        "machine learning": /\bmachine\s*learning\b|\bml\b/
    };
    const matched = [];
    Object.keys(skillsRegex).forEach(sk => {
        if (skillsRegex[sk].test(resumeText)) {
            matched.push(sk);
        }
    });
    return matched;
}

function showJobDetails(job) {
    const detailPanel = document.getElementById("job-detail-panel");
    
    const salVal = (job.salary_min && job.salary_max) 
        ? `$${job.salary_min.toLocaleString()} - $${job.salary_max.toLocaleString()}`
        : "Competitive Salary";
        
    const avgSalVal = job.salary_avg ? `$${job.salary_avg.toLocaleString()}` : "N/A";
    
    // Check match for active resume skills
    const matchedResumeSkills = getMatchedResumeSkills();
    const skillsRequiredHTML = (job.skills || []).map(s => {
        const isMatched = matchedResumeSkills.includes(s.toLowerCase());
        return `<span class="skill-badge${isMatched ? ' matched' : ''}" style="font-size:0.8rem; padding: 4px 10px;">${s}${isMatched ? ' ✓' : ''}</span>`;
    }).join(" ");

    detailPanel.innerHTML = `
        <div class="job-detail-header fade-in">
            <h3>${job.title}</h3>
            <div class="job-detail-company">🏢 ${job.company_name} | Industry: ${job.industry}</div>
        </div>
        
        <div class="job-detail-meta-grid fade-in">
            <div class="detail-meta-item">
                <div class="detail-meta-label">Location</div>
                <div class="detail-meta-value">📍 ${job.location}</div>
            </div>
            <div class="detail-meta-item">
                <div class="detail-meta-label">Experience Required</div>
                <div class="detail-meta-value">💼 ${job.experience_level} (${job.experience_years ? job.experience_years + ' years' : 'Unspecified'})</div>
            </div>
            <div class="detail-meta-item">
                <div class="detail-meta-label">Salary Range (Annual)</div>
                <div class="detail-meta-value salary">${salVal}</div>
            </div>
            <div class="detail-meta-item">
                <div class="detail-meta-label">Average Annual Base</div>
                <div class="detail-meta-value">${avgSalVal}</div>
            </div>
        </div>

        <div class="job-detail-section fade-in">
            <h4>Skills Detected</h4>
            <div style="display:flex; flex-wrap:wrap; gap:8px;">
                ${skillsRequiredHTML || '<span style="color:var(--text-secondary); font-size:0.9rem">No technical skill tags indexed.</span>'}
            </div>
        </div>

        <div class="job-detail-section fade-in">
            <h4>Full Unstructured Job Description</h4>
            <div class="job-detail-desc">${job.description}</div>
        </div>
    `;
}

function renderPaginationControls(current, total) {
    const buttonsContainer = document.getElementById("jobs-pagination-buttons");
    buttonsContainer.innerHTML = "";

    const prevBtn = document.createElement("button");
    prevBtn.className = "btn";
    prevBtn.style.padding = "6px 12px";
    prevBtn.disabled = current === 1;
    prevBtn.innerHTML = "&laquo; Prev";
    prevBtn.addEventListener("click", () => {
        if (jobsCurrentPage > 1) {
            jobsCurrentPage--;
            loadJobsExplorer();
        }
    });
    buttonsContainer.appendChild(prevBtn);

    const nextBtn = document.createElement("button");
    nextBtn.className = "btn";
    nextBtn.style.padding = "6px 12px";
    nextBtn.disabled = current === total || total === 0;
    nextBtn.innerHTML = "Next &raquo;";
    nextBtn.addEventListener("click", () => {
        if (jobsCurrentPage < total) {
            jobsCurrentPage++;
            loadJobsExplorer();
        }
    });
    buttonsContainer.appendChild(nextBtn);
}


// ==================================================
// VIEW 3: SQL PLAYGROUND
// ==================================================
const PRESET_QUERIES = {
    "industry-avg": `SELECT c.industry, \n       COUNT(j.job_id) AS openings,\n       ROUND(AVG(j.salary_avg), 2) AS avg_salary\nFROM job_postings j\nJOIN companies c ON j.company_id = c.company_id\nGROUP BY c.industry\nORDER BY avg_salary DESC;`,
    
    "skill-demand-exp": `SELECT s.skill_name, \n       j.experience_level,\n       COUNT(j.job_id) AS mentions\nFROM skills_required s\nJOIN job_postings j ON s.job_id = j.job_id\nGROUP BY s.skill_name, j.experience_level\nORDER BY mentions DESC;`,
    
    "highest-paying": `SELECT j.title, \n       c.name AS company, \n       j.salary_max, \n       j.experience_years,\n       j.location\nFROM job_postings j\nJOIN companies c ON j.company_id = c.company_id\nWHERE j.salary_max IS NOT NULL\nORDER BY j.salary_max DESC\nLIMIT 10;`,
    
    "skill-cooccurrence": `SELECT s1.skill_name AS skill_a, \n       s2.skill_name AS skill_b,\n       COUNT(*) AS co_occurrence\nFROM skills_required s1\nJOIN skills_required s2 ON s1.job_id = s2.job_id AND s1.skill_name < s2.skill_name\nGROUP BY s1.skill_name, s2.skill_name\nORDER BY co_occurrence DESC;`,
    
    "geographic": `SELECT location, \n       COUNT(*) AS openings,\n       ROUND(AVG(salary_avg), 2) AS avg_salary,\n       MAX(salary_max) AS max_salary\nFROM job_postings\nGROUP BY location\nORDER BY openings DESC;`
};

function initSQLPlayground() {
    const btnRun = document.getElementById("btn-run-sql");
    const inputQuery = document.getElementById("sql-query-input");
    const presetBtns = document.querySelectorAll(".sql-preset-btn");
    const btnExport = document.getElementById("btn-export-sql-csv");

    // Load initial default SQL query
    inputQuery.value = PRESET_QUERIES["industry-avg"];

    presetBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const qId = btn.getAttribute("data-query-id");
            if (PRESET_QUERIES[qId]) {
                inputQuery.value = PRESET_QUERIES[qId];
                runSQL(PRESET_QUERIES[qId]);
            }
        });
    });

    btnRun.addEventListener("click", () => {
        runSQL(inputQuery.value);
    });

    btnExport.addEventListener("click", exportSQLResultsToCSV);
}

async function runSQL(sqlText) {
    const statusText = document.getElementById("sql-status");
    const resultsTable = document.getElementById("sql-results-table");
    const btnExport = document.getElementById("btn-export-sql-csv");

    if (!isLiveAPI) {
        statusText.textContent = "Offline Mode: Custom SQL compilation requires FastAPI backend sqlite connections.";
        statusText.className = "sql-status-bar error";
        resultsTable.innerHTML = "";
        btnExport.style.display = "none";
        return;
    }

    statusText.textContent = "Compiling and executing SELECT query...";
    statusText.className = "sql-status-bar";
    btnExport.style.display = "none";

    try {
        const response = await fetch(`${API_BASE}/api/sql/query`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: sqlText })
        });
        
        const res = await response.json();
        
        if (response.status === 400) {
            statusText.textContent = res.detail;
            statusText.className = "sql-status-bar error";
            resultsTable.innerHTML = "";
            return;
        }

        if (!res.success) {
            statusText.textContent = res.error;
            statusText.className = "sql-status-bar error";
            resultsTable.innerHTML = "";
            return;
        }

        // Cache results for CSV export
        lastSQLResults = res;

        // Render success stats
        statusText.textContent = `Query executed successfully in ${res.elapsed_ms}ms. Returned ${res.row_count} row(s). (Preview limited to first 500 rows)`;
        statusText.className = "sql-status-bar";

        if (res.data.length > 0) {
            btnExport.style.display = "inline-flex";
        }

        // Draw Table
        resultsTable.innerHTML = "";
        
        // Headers
        const thead = document.createElement("thead");
        const trHead = document.createElement("tr");
        res.columns.forEach(col => {
            const th = document.createElement("th");
            th.textContent = col;
            trHead.appendChild(th);
        });
        thead.appendChild(trHead);
        resultsTable.appendChild(thead);

        // Body rows
        const tbody = document.createElement("tbody");
        res.data.forEach(row => {
            const tr = document.createElement("tr");
            res.columns.forEach(col => {
                const td = document.createElement("td");
                const val = row[col];
                td.textContent = val !== null ? val : "NULL";
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        resultsTable.appendChild(tbody);

    } catch (e) {
        console.error("SQL Compilation error:", e);
        statusText.textContent = "Network error connecting to API database compiler.";
        statusText.className = "sql-status-bar error";
        resultsTable.innerHTML = "";
    }
}

function exportSQLResultsToCSV() {
    if (!lastSQLResults || !lastSQLResults.data || lastSQLResults.data.length === 0) return;

    const columns = lastSQLResults.columns;
    const data = lastSQLResults.data;

    // Header row
    let csvRows = [columns.join(",")];

    // Data rows
    data.forEach(row => {
        const values = columns.map(col => {
            const cell = row[col] !== null ? row[col] : "";
            // Escape double quotes and wrap in quotes if contains commas/newlines
            const escaped = ('' + cell).replace(/"/g, '""');
            return `"${escaped}"`;
        });
        csvRows.push(values.join(","));
    });

    const csvContent = csvRows.join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `sql_analyst_report_${Math.floor(Date.now() / 1000)}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}


// ==================================================
// VIEW 4: RESUME MATCH & ML ESTIMATOR
// ==================================================
function initResumePredictor() {
    const btnMatch = document.getElementById("btn-match");
    if (!btnMatch) return;

    btnMatch.addEventListener("click", runResumeAnalysis);
}

async function runResumeAnalysis() {
    const resumeText = document.getElementById("resume-input").value;
    const expYears = Math.max(0, parseInt(document.getElementById("experience-input").value) || 0);

    const scoreVal = document.getElementById("match-score");
    const salaryVal = document.getElementById("predicted-salary");
    const gapList = document.getElementById("gap-skills-list");

    if (isLiveAPI) {
        try {
            scoreVal.textContent = "Calcul...";
            salaryVal.textContent = "Calculating...";
            
            const response = await fetch(`${API_BASE}/api/predict-salary`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    resume_text: resumeText,
                    experience_years: expYears
                })
            });

            const data = await response.json();

            // Populate UI
            scoreVal.textContent = data.match_percent + "%";
            salaryVal.textContent = "$" + Math.round(data.estimated_salary).toLocaleString();

            gapList.innerHTML = "";
            data.skills_analysis.forEach(item => {
                const li = document.createElement("li");
                li.className = "gap-item" + (item.matched ? " matched" : "");
                
                const skillSpan = document.createElement("span");
                skillSpan.className = "gap-skill";
                skillSpan.textContent = item.skill + (item.matched ? " (Matched)" : " (Missing)");
                
                const valSpan = document.createElement("span");
                valSpan.className = "gap-value" + (item.matched ? " matched" : "");
                
                if (item.matched) {
                    valSpan.textContent = "+$" + Math.round(item.value_addition).toLocaleString() + " added";
                } else {
                    valSpan.textContent = "+$" + Math.round(item.value_addition).toLocaleString() + " boost";
                }
                
                li.appendChild(skillSpan);
                li.appendChild(valSpan);
                gapList.appendChild(li);
            });

        } catch (e) {
            console.error("Error predicting resume salary value:", e);
            runClientSideMLPredictor(resumeText, expYears);
        }
    } else {
        // Fallback offline estimation
        runClientSideMLPredictor(resumeText, expYears);
    }
}

// Offline ML prediction client-side algorithm
function runClientSideMLPredictor(resumeText, expYears) {
    const scoreVal = document.getElementById("match-score");
    const salaryVal = document.getElementById("predicted-salary");
    const gapList = document.getElementById("gap-skills-list");

    const rText = resumeText.toLowerCase();
    const weights = FALLBACK_MODEL_WEIGHTS;
    
    const skillsRegex = {
        "SQL": /\bsql\b/,
        "Python": /\bpython\b/,
        "Tableau": /\btableau\b/,
        "Power BI": /\bpower\s*bi\b|\bpbi\b|\bpowerbi\b/,
        "Excel": /\bexcel\b/,
        "Machine Learning": /\bmachine\s*learning\b|\bml\b/
    };
    
    let matchCount = 0;
    const skillMatches = {};
    
    Object.keys(skillsRegex).forEach(skill => {
        const hasSkill = skillsRegex[skill].test(rText);
        skillMatches[skill] = hasSkill;
        if (hasSkill) matchCount++;
    });
    
    const matchPercent = Math.round((matchCount / 6) * 100);
    
    // Calculate regression
    let estimatedSalary = weights.intercept;
    estimatedSalary += weights.experience_year_value * expYears;
    
    Object.keys(skillMatches).forEach(skill => {
        if (skillMatches[skill]) {
            estimatedSalary += weights[skill] || 0;
        }
    });

    scoreVal.textContent = matchPercent + "%";
    salaryVal.textContent = "$" + Math.round(estimatedSalary).toLocaleString();

    // Render list
    gapList.innerHTML = "";
    
    const skillAnalysis = Object.keys(skillsRegex).map(skill => {
        return {
            skill: skill,
            matched: skillMatches[skill],
            value: weights[skill] || 0
        };
    });
    
    // Sort matched first, then missing by descending value
    skillAnalysis.sort((a, b) => {
        if (a.matched === b.matched) return b.value - a.value;
        return a.matched ? -1 : 1;
    });

    skillAnalysis.forEach(item => {
        const li = document.createElement("li");
        li.className = "gap-item" + (item.matched ? " matched" : "");
        
        const skillSpan = document.createElement("span");
        skillSpan.className = "gap-skill";
        skillSpan.textContent = item.skill + (item.matched ? " (Matched)" : " (Missing)");
        
        const valSpan = document.createElement("span");
        valSpan.className = "gap-value" + (item.matched ? " matched" : "");
        
        if (item.matched) {
            valSpan.textContent = "+$" + Math.round(item.value).toLocaleString() + " added";
        } else {
            valSpan.textContent = "+$" + Math.round(item.value).toLocaleString() + " boost";
        }
        
        li.appendChild(skillSpan);
        li.appendChild(valSpan);
        gapList.appendChild(li);
    });
}
