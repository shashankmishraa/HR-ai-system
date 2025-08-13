# app/api.py
import os
from flask import Flask, request, jsonify
import pandas as pd

from app.app_utils import evaluate_candidate
from utils.matcher import compute_matches
from utils.rl_agent import load_q_table, decide_action

app = Flask(__name__)

# ---- Paths to CSVs (relative to project root) ----
ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_CVS = os.path.join(ROOT, "data", "sample_cvs.csv")
DATA_JDS = os.path.join(ROOT, "data", "sample_jds.csv")
DATA_FEEDBACKS = os.path.join(ROOT, "data", "sample_feedbacks.csv")

# Try to load a previously trained Q-table (optional)
Q_TABLE = load_q_table()  # returns None if not found; we fall back to a rule

# ---- Data helpers ----
def load_cv_by_id(cv_id):
    cvs = pd.read_csv(DATA_CVS)
    row = cvs[cvs["id"] == cv_id]
    if row.empty:
        return None
    return row.iloc[0].to_dict()

def load_jd_by_id(jd_id):
    jds = pd.read_csv(DATA_JDS)
    row = jds[jds["id"] == jd_id]
    if row.empty:
        return None
    return row.iloc[0].to_dict()

def load_feedbacks_for_candidate(cv_id):
    if not os.path.exists(DATA_FEEDBACKS):
        return []
    fb = pd.read_csv(DATA_FEEDBACKS)
    return (
        fb[fb["candidate_id"] == cv_id]["feedback_text"]
        .dropna()
        .astype(str)
        .tolist()
    )

# ---- Routes ----

@app.route("/evaluate", methods=["POST"])
def evaluate():
    """
    Accept either:
      - cv_text + jd_text
      - or cv_id + jd_id  (auto-lookup from data/*.csv)
    Optional: feedbacks list.
    Returns: evaluation dict (from evaluate_candidate) with cv/jd metadata filled.
    """
    payload = request.get_json() or {}

    cv_id = payload.get("cv_id") or payload.get("candidate_id")
    jd_id = payload.get("jd_id") or payload.get("job_id")

    cv_text = payload.get("cv_text", "")
    jd_text = payload.get("jd_text", "")
    cv_meta = payload.get("cv_meta", {})
    jd_meta = payload.get("jd_meta", {})
    feedbacks = payload.get("feedbacks", [])

    if cv_id:
        cv_row = load_cv_by_id(cv_id)
        if cv_row:
            cv_text = cv_text or str(cv_row.get("resume_text", ""))
            cv_meta.update({
                "id": cv_row.get("id", ""),
                "name": cv_row.get("name", ""),
                "location": cv_row.get("location", ""),
                "experience_months": cv_row.get("experience_months", 0),
                "education": cv_row.get("education", ""),
                "skills": cv_row.get("skills", "")
            })
        if not feedbacks:
            feedbacks = load_feedbacks_for_candidate(cv_id)

    if jd_id:
        jd_row = load_jd_by_id(jd_id)
        if jd_row:
            jd_text = jd_text or (str(jd_row.get("description", "")) + " " + str(jd_row.get("required_skills", "")))
            jd_meta.update({
                "id": jd_row.get("id", ""),
                "title": jd_row.get("title", ""),
                "location": jd_row.get("location", ""),
                "required_skills": jd_row.get("required_skills", "")
            })

    result = evaluate_candidate(cv_text, jd_text, cv_meta=cv_meta, jd_meta=jd_meta, feedback_texts=feedbacks)

    # Ensure clarity fields:
    result["cv_id"] = cv_meta.get("id", cv_id or "")
    result["cv_name"] = cv_meta.get("name", result.get("cv_name", ""))
    result["jd_id"] = jd_meta.get("id", jd_id or "")
    result["jd_title"] = jd_meta.get("title", result.get("jd_title", ""))

    return jsonify(result)

@app.route("/decide", methods=["POST"])
def decide():
    """
    Same payload as /evaluate, but returns an extra RL decision:
    {
      ... <evaluate fields> ...,
      "rl_action": "HIRE" | "REJECT" | "ASSIGN_TASK" | "HOLD",
      "decision_source": "RL" | "RULE_FALLBACK"
    }
    """
    payload = request.get_json() or {}

    # Reuse evaluate() logic to compute features
    resp = app.test_client().post("/evaluate", json=payload)
    if resp.status_code != 200:
        return jsonify({"error": "evaluation failed"}), 400
    eval_result = resp.get_json()

    # Decide action via RL (or fallback rule if no Q-table)
    rl = decide_action(eval_result, Q=Q_TABLE, prev_action="REJECT")
    src = "RL" if Q_TABLE is not None else "RULE_FALLBACK"

    eval_result["rl_action"] = rl
    eval_result["decision_source"] = src
    return jsonify(eval_result)

@app.route("/top_candidates", methods=["GET"])
def top_candidates():
    """
    Query params:
      - jd_id (optional): filter to this JD
      - top_n (optional): default 10
    """
    jd_id = request.args.get("jd_id")
    top_n = int(request.args.get("top_n", 10))

    cvs = pd.read_csv(DATA_CVS)
    jds = pd.read_csv(DATA_JDS)

    matches = compute_matches(cvs, jds, top_k=top_n)
    if jd_id:
        matches = matches[matches["jd_id"] == jd_id]

    matches = matches.sort_values("rank")
    out = []
    for _, r in matches.iterrows():
        cv_row = cvs[cvs["id"] == r["cv_id"]]
        snippet = ""
        if not cv_row.empty:
            snippet = str(cv_row.iloc[0].get("resume_text", ""))[:300]
        out.append({
            "jd_id": r["jd_id"],
            "jd_title": r.get("jd_title", ""),
            "cv_id": r["cv_id"],
            "cv_name": r.get("cv_name", ""),
            "rank": int(r["rank"]),
            "base_score": float(r.get("base_score", 0.0)),
            "score": float(r.get("score", r.get("base_score", 0.0))),
            "skill_overlap": int(r.get("skill_overlap", 0)),
            "location_match": bool(r.get("location_match", 0)),
            "resume_snippet": snippet
        })
    return jsonify(out)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
