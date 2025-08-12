import os, sys, json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
from utils.text_preproc import clean_text, extract_skills, parse_experience, education_score
from utils.embedding import embed_corpus
from utils.sentiment import sentiment_score
from utils.rl_agent import discretize_state, train_q, save_q_table, load_q_table, select_action_from_q
import numpy as np
from datetime import datetime
Q_TABLE_PATH = os.path.join('models','q_table.pkl')
def baseline_compatibility(sim_score, skill_overlap, location_flag, exp_norm, edu_score):
    sc = 0.6*sim_score + 0.2*(skill_overlap / 5.0) + 0.1*location_flag + 0.1*exp_norm
    return max(0.0, min(1.0, sc))
def ensure_q_table():
    if os.path.exists(Q_TABLE_PATH):
        try:
            Q = load_q_table(Q_TABLE_PATH)
            return Q
        except Exception:
            pass
    Q = train_q(episodes=1200)
    save_q_table(Q, Q_TABLE_PATH)
    return Q
def evaluate_candidate(cv_text, jd_text, cv_meta=None, jd_meta=None, feedback_texts=None):
    cv_meta = cv_meta or {}
    jd_meta = jd_meta or {}
    feedback_texts = feedback_texts or []
    cv_text_clean = clean_text(cv_text)
    jd_text_clean = clean_text(jd_text)
    cv_skills = extract_skills(cv_text_clean)
    jd_skills = extract_skills(jd_text_clean)
    skill_overlap = len(set(cv_skills).intersection(set(jd_skills)))
    loc_flag = 1 if (str(cv_meta.get('location','')).strip().lower() == str(jd_meta.get('location','')).strip().lower()) or (str(cv_meta.get('location','')).strip().lower()=='remote') else 0
    exp = parse_experience(cv_meta.get('experience_months', 0))
    exp_norm = min(1.0, exp / 120.0)
    edu_score = education_score(cv_meta.get('education',''))
    emb_cv, emb_jd = embed_corpus([cv_text_clean], [jd_text_clean])
    cos = float(np.dot(emb_cv[0], emb_jd[0]) / (np.linalg.norm(emb_cv[0]) * np.linalg.norm(emb_jd[0]) + 1e-9))
    sim_score = max(0.0, min(1.0, (cos + 1)/2)) if np.isfinite(cos) else 0.0
    base_score = baseline_compatibility(sim_score, skill_overlap, loc_flag, exp_norm, edu_score)
    sentiments = [sentiment_score(t) for t in feedback_texts]
    avg_sent = float(np.mean(sentiments)) if sentiments else 0.0
    alignment = 1.0 - abs(avg_sent - 0.0)
    Q = ensure_q_table()
    state = discretize_state(sim_score, avg_sent, exp_norm, loc_flag, prev_action=3)
    action_idx, action_name = select_action_from_q(Q, state)
    explanation = [
        f'similarity: {sim_score:.3f}',
        f'skill_overlap: {skill_overlap}',
        f'experience_months: {exp}',
        f'location_match: {bool(loc_flag)}',
        f'baseline_score: {base_score:.3f}'
    ]
    result = {
        'cv_id': cv_meta.get('id',''),
        'cv_name': cv_meta.get('name',''),
        'jd_id': jd_meta.get('id',''),
        'match_score': base_score,
        'similarity': sim_score,
        'sentiment': avg_sent,
        'alignment': alignment,
        'agent_decision': action_name,
        'explanation': explanation,
        'timestamp': datetime.utcnow().isoformat()
    }
    os.makedirs('outputs', exist_ok=True)
    outfn = os.path.join('outputs', f'run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    with open(outfn, 'w') as f:
        json.dump(result, f, indent=2)
    return result
