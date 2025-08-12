# HR AI System - Ready-to-Run (Windows)

## Overview
This repository contains a minimal, working HR AI MVP: embedding-based CV↔JD matching,
sentiment analysis (VADER), a simple RL agent (tabular Q-learning), and a Flask API
exposing an `/evaluate` endpoint. It uses synthetic sample data.

## Quick setup (PowerShell in VS Code)
1. Open a terminal in the project folder.
2. Create & activate virtualenv:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   If activation is blocked, run PowerShell as admin and:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned
   ```
3. Install dependencies:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   # If sentence-transformers fails because torch is missing:
   pip install torch --index-url https://download.pytorch.org/whl/cpu
   pip install sentence-transformers
   ```
4. Download NLTK data:
   ```powershell
   python -m nltk.downloader punkt vader_lexicon
   ```
5. Generate sample data:
   ```powershell
   python utils\generate_sample_data.py
   ```
6. Run a quick pipeline test:
   ```powershell
   python run_pipeline.py
   ```
7. Run the Flask API:
   ```powershell
   python -m app.api
   ```

## Files of interest
- `utils/` : helper modules (preprocessing, embedding, matcher, sentiment, RL)
- `app/` : API and decision glue (app/api.py, app/utils.py)
- `data/` : synthetic sample data
- `models/` : saved models & q-table
- `outputs/` : match results, run json files, charts

## How to test the API (PowerShell example)
```powershell
$body = @{
  cv_text = "Experienced Python ML engineer with NLP projects and SQL."
  jd_text = "Looking for Python ML engineer with NLP and SQL."
  cv_meta = @{ id="c-001"; name="Alice"; location="Remote"; experience_months=36; education="B.Tech"; skills="python,ml,nlp,sql" }
  jd_meta = @{ id="jd-99"; title="ML Eng"; location="Remote"; required_skills="python,ml,nlp,sql" }
  feedbacks = @("Strong ML fundamentals", "Good communication")
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri http://127.0.0.1:5000/evaluate -Method POST -Body $body -ContentType 'application/json'
```

## Notes
- The project uses SentenceTransformers if available; otherwise falls back to TF-IDF+SVD.
- RL is trained on a simulated environment — it's for demonstration only.
- Keep outputs small for submission (remove large model files if necessary).
