# Candidate Matching + Reinforcement Learning Hiring Demo (Windows, VS Code)

## Overview
This repository contains a **ready-to-run HR AI system** with:
- **Embedding-based CV↔JD matching** (SentenceTransformers or TF-IDF fallback)
- **Sentiment Analysis** (NLTK VADER)
- **Tabular Q-learning RL agent** for hire decision-making
- **Flask API** exposing `/evaluate`, `/top_candidates`, `/decide` endpoints
- **Interactive PowerShell demo script** (`run_demo.ps1`) to simulate hiring flow

It ships with **synthetic sample data** so you can try it out immediately.

---

## Quick Setup (PowerShell in VS Code)

### 1. Clone repository
```powershell
git clone <your_repo_url> C:\Task_Aiml_Intern
cd C:\Task_Aiml_Intern
```

### 2. Create & activate virtualenv
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
If activation is blocked:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned
```

### 3. Install dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
# If sentence-transformers fails because torch is missing:
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers
```

### 4. Download NLTK data
```powershell
python -m nltk.downloader punkt vader_lexicon
```

### 5. Generate sample data
```powershell
python utils\generate_sample_data.py
```

### 6. Train the RL Agent
```powershell
.\.venv\Scripts\python.exe
```
Inside Python:
```python
from utils.rl_agent import train_q, save_q_table
Q = train_q(episodes=2000)
path = save_q_table(Q)
print("Saved Q-table to:", path)
exit()
```

### 7. Run a quick pipeline test
```powershell
python run_pipeline.py
```

### 8. Start the Flask API
```powershell
python -m app.api
```
You should see:
```
 * Running on http://127.0.0.1:5000
```

---

## How to Test API (Example)
```powershell
$body = @{ cv_id = "d6f2cc3d"; jd_id = "JD_8" } | ConvertTo-Json -Compress
Invoke-RestMethod -Uri "http://127.0.0.1:5000/decide" -Method POST -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 6
```

Example response:
```json
{
  "cv_id": "d6f2cc3d",
  "jd_id": "JD_8",
  "match_score": 0.82,
  "sentiment": 0.74,
  "rl_action": "HIRE",
  "decision_source": "RL"
}
```

---

## Running the Interactive Demo
With the API running, in another VS Code terminal:
```powershell
.\run_demo.ps1
```
Follow prompts to run for **all** or **one** JD.

Sample output:
```
===== TOP 5 CANDIDATES for JD_8 =====
1) 07e54d6f | Score: 0.776 | Skills: 3 | LocationMatch: True
    RL Decision: HIRE (Source: RL)
...

===== SELECTED HIRE for JD_8 =====
[HIRE] 07e54d6f | Score: 0.776 | Skills: 3 | LocationMatch: True
    RL Decision: HIRE (Source: RL)

===== SAVED 1 HIRED ROW(S) to C:\Task_Aiml_Intern\data\hired_candidates.csv =====
```

---

## Files of Interest
- `utils/` : helper modules (embedding, sentiment, RL, data generation)
- `app/` : API and business logic
- `data/` : synthetic CVs, JDs, feedback
- `models/` : saved Q-tables
- `run_demo.ps1` : interactive CLI demo

---

## Troubleshooting
- **`ModuleNotFoundError: No module named 'utils'`** → Run from project root, ensure `utils/__init__.py` exists.
- **`RULE_FALLBACK` in `/decide`** → Train RL agent before starting API.
- **`API not reachable`** → Ensure `python -m app.api` is running in another terminal.
- **`python` not recognized** → Use `.\.venv\Scripts\python.exe`.

---

## Credits
Developed by **Shashank Mishra** — BE AIML, Vasai, Maharashtra,India.
