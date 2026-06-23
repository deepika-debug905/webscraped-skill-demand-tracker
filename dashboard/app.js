// ==================================================
// Job Market & Skill Demand Predictor
// Dashboard Visualizations with Chart.js
// ==================================================

// Fallback model weights for interactive estimation
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

// 1. Portfolio Demonstration Data (Fallback if database pipeline is not run yet)
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

// Global chart font and layout configurations
Chart.defaults.color = '#9ca3af';
Chart.defaults.font.family = "'Outfit', sans-serif";
Chart.defaults.font.size = 12;

document.addEventListener("DOMContentLoaded", () => {
    // 2. Determine if live database data is available
    let activeData = DEMO_DATA;
    let isLive = false;

    if (typeof DATA !== 'undefined' && DATA && DATA.kpis) {
        activeData = DATA;
        isLive = true;
        console.log("[Dashboard] Successfully loaded live SQL-generated pipeline data!");
    } else {
        console.log("[Dashboard] Live data not detected, loading portfolio demo dataset.");
    }

    // 3. Inject Connection Status Indicator and populate KPIs
    injectStatusIndicator(isLive);
    populateKPIs(activeData.kpis);

    // 4. Render the 4 Visualizations
    renderBIPositioning(activeData.bi_tools);
    renderPremiumSkills(activeData.premium_skills);
    renderIndustries(activeData.industries);
    renderCareerVelocity(activeData.experience_salary);

    // 5. Initialize Resume Matcher & ML Salary Estimator
    initResumeMatcher();
});

function injectStatusIndicator(isLive) {
    const header = document.querySelector(".header-title");
    const statusDiv = document.createElement("div");
    
    statusDiv.style.display = "inline-flex";
    statusDiv.style.alignItems = "center";
    statusDiv.style.gap = "6px";
    statusDiv.style.fontSize = "0.8rem";
    statusDiv.style.fontWeight = "600";
    statusDiv.style.marginTop = "8px";
    statusDiv.style.padding = "4px 8px";
    statusDiv.style.borderRadius = "4px";
    
    if (isLive) {
        statusDiv.style.backgroundColor = "rgba(16, 185, 129, 0.15)";
        statusDiv.style.color = "#10b981";
        statusDiv.innerHTML = `<span style="display:inline-block; width:8px; height:8px; background-color:#10b981; border-radius:50%"></span> LIVE PIPELINE DATABASE DATA`;
    } else {
        statusDiv.style.backgroundColor = "rgba(245, 158, 11, 0.15)";
        statusDiv.style.color = "#f59e0b";
        statusDiv.innerHTML = `<span style="display:inline-block; width:8px; height:8px; background-color:#f59e0b; border-radius:50%"></span> PIPELINE DEMO DATA`;
        
        // Show file setup note warning
        document.getElementById("no-data-alert").style.display = "block";
    }
    
    header.appendChild(statusDiv);
}

function populateKPIs(kpis) {
    document.getElementById("kpi-total-jobs").textContent = kpis.total_jobs;
    document.getElementById("kpi-avg-salary").textContent = "$" + kpis.average_salary.toLocaleString();
    document.getElementById("kpi-top-skill").textContent = kpis.top_skill;
}

// Visualisation 1: Power BI vs Tableau (Donut)
function renderBIPositioning(biData) {
    const ctx = document.getElementById("chart-bi-battle").getContext("2d");
    
    const pbCount = biData["Power BI"] || 0;
    const tabCount = biData["Tableau"] || 0;
    
    // Calculate percentages
    const total = pbCount + tabCount;
    const pbPercent = total > 0 ? Math.round((pbCount / total) * 100) : 0;
    const tabPercent = total > 0 ? Math.round((tabCount / total) * 100) : 0;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: [`Power BI (${pbCount} jobs)`, `Tableau (${tabCount} jobs)`],
            datasets: [{
                data: [pbCount, tabCount],
                backgroundColor: ['#f59e0b', '#3b82f6'],
                borderColor: '#141a2e',
                borderWidth: 3,
                hoverOffset: 12
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        font: { size: 13, weight: '500' }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const val = context.raw;
                            const pct = Math.round((val / total) * 100);
                            return ` ${context.label.split(' (')[0]}: ${val} mentions (${pct}%)`;
                        }
                    }
                }
            },
            cutout: '70%'
        }
    });
}

// Visualisation 2: Premium Skill Salaries (Bar chart)
function renderPremiumSkills(skillsData) {
    const ctx = document.getElementById("chart-premium-skills").getContext("2d");
    
    // Extract labels and data
    const labels = skillsData.map(item => item.skill);
    const salaries = skillsData.map(item => item.avg_salary);
    const counts = skillsData.map(item => item.job_count);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Annual Salary',
                data: salaries,
                backgroundColor: 'rgba(139, 92, 246, 0.7)',
                borderColor: '#8b5cf6',
                borderWidth: 1.5,
                borderRadius: 6,
                hoverBackgroundColor: 'rgba(139, 92, 246, 0.95)',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        callback: value => '$' + (value / 1000) + 'k'
                    }
                },
                x: {
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const idx = context.dataIndex;
                            return ` Avg Salary: $${context.raw.toLocaleString()} | Jobs: ${counts[idx]}`;
                        }
                    }
                }
            }
        }
    });
}

// Visualisation 3: Industry Concentration (Horizontal bar)
function renderIndustries(industryData) {
    const ctx = document.getElementById("chart-industries").getContext("2d");
    
    const labels = industryData.map(item => item.industry);
    const counts = industryData.map(item => item.job_count);
    const salaries = industryData.map(item => item.avg_salary);

    new Chart(ctx, {
        type: 'bar',
        indexAxis: 'y',
        data: {
            labels: labels,
            datasets: [{
                label: 'Openings Scraped',
                data: counts,
                backgroundColor: 'rgba(16, 185, 129, 0.7)',
                borderColor: '#10b981',
                borderWidth: 1.5,
                borderRadius: 6,
                hoverBackgroundColor: 'rgba(16, 185, 129, 0.95)',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { stepSize: 10 }
                },
                y: {
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const idx = context.dataIndex;
                            return ` Postings: ${context.raw} | Avg Salary: $${salaries[idx].toLocaleString()}`;
                        }
                    }
                }
            }
        }
    });
}

// Visualisation 4: Experience vs Salary bounds (Stacked range or multi-line)
function renderCareerVelocity(expData) {
    const ctx = document.getElementById("chart-experience-salary").getContext("2d");
    
    const labels = expData.map(item => item.level);
    const averages = expData.map(item => item.avg_salary);
    const mins = expData.map(item => item.min_salary);
    const maxs = expData.map(item => item.max_salary);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Maximum Bound',
                    data: maxs,
                    borderColor: 'rgba(239, 68, 68, 0.6)',
                    backgroundColor: 'transparent',
                    borderDash: [5, 5],
                    pointBackgroundColor: '#ef4444',
                    borderWidth: 2,
                    tension: 0.2
                },
                {
                    label: 'Average Rate',
                    data: averages,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    pointBackgroundColor: '#3b82f6',
                    pointRadius: 6,
                    pointHoverRadius: 8,
                    borderWidth: 4,
                    fill: true,
                    tension: 0.2
                },
                {
                    label: 'Minimum Bound',
                    data: mins,
                    borderColor: 'rgba(16, 185, 129, 0.6)',
                    backgroundColor: 'transparent',
                    borderDash: [5, 5],
                    pointBackgroundColor: '#10b981',
                    borderWidth: 2,
                    tension: 0.2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        callback: value => '$' + (value / 1000) + 'k'
                    }
                },
                x: {
                    grid: { display: false }
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 12, padding: 15 }
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

function initResumeMatcher() {
    const btnMatch = document.getElementById("btn-match");
    if (!btnMatch) return;
    
    btnMatch.addEventListener("click", () => {
        const resumeText = (document.getElementById("resume-input").value || "").toLowerCase();
        const expYears = Math.max(0, parseInt(document.getElementById("experience-input").value) || 0);
        
        // Load model weights (use fallback if live model isn't generated)
        let weights = FALLBACK_MODEL_WEIGHTS;
        if (typeof MODEL_WEIGHTS !== 'undefined' && MODEL_WEIGHTS && MODEL_WEIGHTS.intercept) {
            weights = MODEL_WEIGHTS;
        }
        
        // Define regex for each skill
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
        
        // Run match
        Object.keys(skillsRegex).forEach(skill => {
            const hasSkill = skillsRegex[skill].test(resumeText);
            skillMatches[skill] = hasSkill;
            if (hasSkill) matchCount++;
        });
        
        // Calculate match percentage
        const matchPercent = Math.round((matchCount / 6) * 100);
        
        // Calculate estimated salary using ML weights
        let estimatedSalary = weights.intercept;
        estimatedSalary += weights.experience_year_value * expYears;
        
        Object.keys(skillMatches).forEach(skill => {
            if (skillMatches[skill]) {
                estimatedSalary += weights[skill] || 0;
            }
        });
        
        // Display values
        document.getElementById("match-score").textContent = matchPercent + "%";
        document.getElementById("predicted-salary").textContent = "$" + Math.round(estimatedSalary).toLocaleString();
        
        // Sort and render skills analysis (gaps vs matched)
        const gapList = document.getElementById("gap-skills-list");
        gapList.innerHTML = "";
        
        const skillAnalysis = Object.keys(skillsRegex).map(skill => {
            return {
                skill: skill,
                matched: skillMatches[skill],
                value: weights[skill] || 0
            };
        });
        
        // Sort: matched first, then missing skills sorted by highest value addition
        skillAnalysis.sort((a, b) => {
            if (a.matched === b.matched) {
                return b.value - a.value; // Sort by descending salary contribution
            }
            return a.matched ? -1 : 1; // Matched skills first
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
    });
}
