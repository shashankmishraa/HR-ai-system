import re
from typing import List
def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ''
    text = text.lower()
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'[^a-z0-9\s,\.#+\-]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text
def extract_skills(text: str, skills_pool=None) -> List[str]:
    if skills_pool is None:
        skills_pool = ['python','ml','nlp','sql','aws','docker','react','java','c++','pandas','tensorflow']
    text_l = clean_text(text)
    found = []
    for s in skills_pool:
        if re.search(r'\b' + re.escape(s) + r'\b', text_l):
            found.append(s)
    return found
def parse_experience(exp) -> int:
    try:
        return int(float(exp))
    except Exception:
        return 0
def education_score(edu: str) -> float:
    if not isinstance(edu, str): return 0.5
    e = edu.lower()
    if 'phd' in e:
        return 1.0
    if 'm.tech' in e or 'ms' in e or 'm.sc' in e or 'master' in e:
        return 0.9
    if 'b.tech' in e or 'bachelor' in e or 'bsc' in e:
        return 0.7
    return 0.5
