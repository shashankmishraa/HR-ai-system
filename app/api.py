# app/api.py
import os
from flask import Flask, request, jsonify
import pandas as pd

# import the evaluation function (from your app helper)
from app.app_utils import evaluate_candidate
from utils.matcher import compute_matches

app = Flask(__name__)

# paths to CSVs (calculated relative to project root)
ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_CVS = os.path.join(ROOT, "data", "sample_cvs.csv")
DATA_JDS = os.path.join(ROOT, "data", "sample_jds.csv")
DATA_FEEDBACKS = os.path.join(ROOT, "data", "sample_feedbacks.csv")


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
    texts = fb[fb["candidate_id"] == cv_id]["feedback_text"].dropna().astype(str).tolist()
    return texts


@app.route("/evaluate", methods=["POST"])
def evaluate():
    """
    Accepts either:
      - cv_text + jd_text
      - OR cv_id + jd_id  (looks up the texts and metadata from data/*.csv)
    Optional: feedbacks list in payload.
    Returns evaluation dict from evaluate_candidate + ensures cv_id/cv_name/jd_id/jd_title present.
    """
    payload = request.get_json() or {}

    # prefer IDs if passed
    cv_id = payload.get("cv_id") or payload.get("candidate_id")
    jd_id = payload.get("jd_id") or payload.get("job_id")

    cv_text = payload.get("cv_text", "")
    jd_text = payload.get("jd_text", "")
    cv_meta = payload.get("cv_meta", {})
    jd_meta = payload.get("jd_meta", {})
    feedbacks = payload.get("feedbacks", [])

    # If cv_id given, load CV row and populate cv_text / cv_meta
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
        # if feedbacks not provided, attempt to fetch from feedbacks CSV
        if not feedbacks:
            feedbacks = load_feedbacks_for_candidate(cv_id)

    # If jd_id given, load JD row and populate jd_text / jd_meta
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

    # Call the core evaluation function
    result = evaluate_candidate(cv_text, jd_text, cv_meta=cv_meta, jd_meta=jd_meta, feedback_texts=feedbacks)

    # Ensure returned payload contains IDs/names for clarity in demo
    result["cv_id"] = cv_meta.get("id", cv_id or "")
    result["cv_name"] = cv_meta.get("name", result.get("cv_name", ""))
    result["jd_id"] = jd_meta.get("id", jd_id or "")
    result["jd_title"] = jd_meta.get("title", result.get("jd_title", ""))

    return jsonify(result)


@app.route("/top_candidates", methods=["GET"])
def top_candidates():
    """
    Query params:
      - jd_id (optional): filter to this JD
      - top_n (optional, default 10)
    Returns list of matches (ranked) with some metadata and a resume_snippet.
    """
    jd_id = request.args.get("jd_id")
    top_n = int(request.args.get("top_n", 10))

    cvs = pd.read_csv(DATA_CVS)
    jds = pd.read_csv(DATA_JDS)

    matches = compute_matches(cvs, jds, top_k=top_n)

    if jd_id:
        matches = matches[matches["jd_id"] == jd_id]

    # Sort by rank and build output
    matches = matches.sort_values("rank")
    out = []
    for _, r in matches.iterrows():
        # safe extraction of resume snippet
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
    # Run as module: python -m app.api  (recommended)
    app.run(host="0.0.0.0", port=port, debug=True)
