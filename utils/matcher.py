import os, numpy as np, pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
from .embedding import embed_corpus
def compute_matches(cvs_df, jds_df, top_k=5, boost_location=0.05, boost_skill=0.05, save_csv=True):
    cv_texts = cvs_df['resume_text'].astype(str).tolist()
    jd_texts = (jds_df['description'].astype(str).fillna('') + ' ' + jds_df['required_skills'].astype(str)).tolist()
    emb_cv, emb_jd = embed_corpus(cv_texts, jd_texts)
    sims = cosine_similarity(emb_jd, emb_cv)
    rows = []
    for j_idx, jd_row in jds_df.reset_index().iterrows():
        jd_id = jd_row['id']
        jd_loc = str(jd_row.get('location','')).strip().lower()
        jd_skills = [s.strip().lower() for s in str(jd_row.get('required_skills','')).split(',') if s.strip()!='']
        row = sims[j_idx]
        ranked = np.argsort(row)[::-1][:top_k]
        for rank, cv_idx in enumerate(ranked, start=1):
            base_score = float(row[cv_idx])
            cv_row = cvs_df.reset_index().iloc[cv_idx]
            cv_id = cv_row['id']
            cv_loc = str(cv_row.get('location','')).strip().lower()
            cv_skills = [s.strip().lower() for s in str(cv_row.get('skills','')).split(',') if s.strip()!='']
            skill_overlap = len(set(cv_skills).intersection(set(jd_skills)))
            loc_flag = 1 if (jd_loc and cv_loc and (jd_loc==cv_loc or cv_loc=='remote' or jd_loc=='remote')) else 0
            score = base_score + (boost_skill * skill_overlap) + (boost_location * loc_flag)
            score = max(0.0, min(1.0, score))
            rows.append({
                'timestamp': datetime.utcnow().isoformat(),
                'jd_id': jd_id,
                'jd_title': jd_row.get('title',''),
                'cv_id': cv_id,
                'cv_name': cv_row.get('name',''),
                'base_score': base_score,
                'skill_overlap': skill_overlap,
                'location_match': loc_flag,
                'score': score,
                'rank': rank
            })
    df = pd.DataFrame(rows)
    if save_csv:
        os.makedirs('outputs', exist_ok=True)
        fn = os.path.join('outputs', f'match_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
        df.to_csv(fn, index=False)
        print('Saved match results to:', fn)
    return df
