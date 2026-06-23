import sqlite3
import json
import os
import random

# Configuration
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "job_market.db")
MODEL_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "salary_model.json")
MODEL_JS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "salary_model.js")

SKILLS = ["SQL", "Python", "Tableau", "Power BI", "Excel", "Machine Learning"]

# Premium pre-trained fallback weights (to ensure dashboard functions if DB is empty or small)
DEFAULT_WEIGHTS = {
    "intercept": 62500.0,
    "experience_year_value": 4800.0,
    "SQL": 6500.0,
    "Python": 9200.0,
    "Tableau": 5800.0,
    "Power BI": 7800.0,
    "Excel": 2500.0,
    "Machine Learning": 14500.0
}

def train_predictor():
    print("=========================================")
    print("      TRAINING SALARY PREDICTOR MODEL    ")
    print("=========================================")
    
    if not os.path.exists(DB_PATH):
        print(f"[ML] Database not found at {DB_PATH}. Exporting premium default model.")
        save_model(DEFAULT_WEIGHTS)
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Fetch training data (jobs with parsed salary and experience)
    try:
        cursor.execute("""
            SELECT jp.job_id, jp.salary_avg, jp.experience_years
            FROM job_postings jp
            WHERE jp.salary_avg IS NOT NULL AND jp.experience_years IS NOT NULL
        """)
        job_rows = cursor.fetchall()
    except Exception as e:
        print(f"[ML Warning] Could not query jobs: {e}. Exporting premium default model.")
        save_model(DEFAULT_WEIGHTS)
        conn.close()
        return

    if len(job_rows) < 10:
        print(f"[ML] Too few samples ({len(job_rows)}) to train a robust regression model. Exporting premium default weights.")
        save_model(DEFAULT_WEIGHTS)
        conn.close()
        return

    print(f"[ML] Training model on {len(job_rows)} job listings using Gradient Descent...")

    X = []
    y = []

    for row in job_rows:
        job_id, salary_avg, exp_years = row
        
        # Fetch skills for this job
        cursor.execute("SELECT skill_name FROM skills_required WHERE job_id = ?", (job_id,))
        job_skills = {r[0] for r in cursor.fetchall()}
        
        # Construct feature vector:
        # x0: Intercept (1.0)
        # x1: Scaled Experience (years / 10.0 to prevent gradient explosion)
        # x2 to x7: Binary indicators for SKILLS
        x_vector = [
            1.0,
            float(exp_years) / 10.0
        ]
        for skill in SKILLS:
            x_vector.append(1.0 if skill in job_skills else 0.0)
            
        X.append(x_vector)
        # Scale target variable (Salary in thousands, e.g. 98450 -> 98.45) to ensure stable convergence
        y.append(float(salary_avg) / 1000.0)
        
    conn.close()

    # 2. Gradient Descent Model Training (Standard Multiple Linear Regression)
    N = len(X)
    D = len(X[0])
    weights = [0.0] * D
    
    # Training Parameters
    lr = 0.05
    epochs = 4000
    
    for epoch in range(epochs):
        # Compute predictions: X * w
        preds = []
        for i in range(N):
            pred = sum(X[i][j] * weights[j] for j in range(D))
            preds.append(pred)
            
        # Compute errors: pred - y
        errors = [preds[i] - y[i] for i in range(N)]
        
        # Calculate gradients: X^T * errors / N
        gradients = [0.0] * D
        for j in range(D):
            grad_sum = sum(errors[i] * X[i][j] for i in range(N))
            gradients[j] = grad_sum / N
            
        # Update weights
        for j in range(D):
            weights[j] -= lr * gradients[j]
            
        # Log training loss reduction
        if epoch in [0, 999, 1999, 3999]:
            mse = sum(e**2 for e in errors) / N
            print(f"[ML] Epoch {epoch + 1}/{epochs} | MSE Loss: {mse:.4f}")

    # 3. Unscale Weights back to actual Dollar values
    # intercept = w[0] * 1000
    # exp_weight = (w[1] * 1000) / 10 = w[1] * 100
    # skill_weights = w[2:] * 1000
    trained_model = {
        "intercept": round(weights[0] * 1000.0, 2),
        "experience_year_value": round(weights[1] * 100.0, 2)
    }
    
    for idx, skill in enumerate(SKILLS):
        # index offset by 2 due to intercept and experience fields
        trained_model[skill] = round(weights[idx + 2] * 1000.0, 2)
        
    print("[ML] Model training complete. Learned coefficients:")
    print(f"  - Base Salary (Intercept): ${trained_model['intercept']:.2f}")
    print(f"  - Value per Year of Experience: ${trained_model['experience_year_value']:.2f}")
    for skill in SKILLS:
        print(f"  - Value of {skill}: +${trained_model[skill]:.2f}")
        
    save_model(trained_model)

def save_model(model_weights):
    """Saves weights to JSON for backend uses and JS for frontend bypass."""
    # Ensure directories exist
    os.makedirs(os.path.dirname(MODEL_JSON_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(MODEL_JS_PATH), exist_ok=True)
    
    # Save to JSON
    with open(MODEL_JSON_PATH, 'w') as f:
        json.dump(model_weights, f, indent=4)
        
    # Save to JS variable file
    js_content = f"// Automatically generated regression weights for interactive estimation\nconst MODEL_WEIGHTS = {json.dumps(model_weights, indent=4)};"
    with open(MODEL_JS_PATH, 'w') as f:
        f.write(js_content)
        
    print(f"[ML] Exported model JSON to: {MODEL_JSON_PATH}")
    print(f"[ML] Exported model JS to: {MODEL_JS_PATH}")
    print("=========================================")

if __name__ == "__main__":
    train_predictor()
