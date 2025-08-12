import csv, random, uuid, os
os.makedirs('data', exist_ok=True)
skills_pool = ['python','ml','nlp','sql','aws','docker','react','java','c++','pandas','tensorflow']
def make_cv(i):
    sid = str(uuid.uuid4())[:8]
    name = f'Candidate_{i}'
    loc = random.choice(['Mumbai','Bengaluru','Remote','Pune','Delhi'])
    skills = ','.join(random.sample(skills_pool, k=random.randint(3,6)))
    exp = random.randint(6,120)
    edu = random.choice(['B.Tech','M.Tech','BSc','MCA'])
    resume_text = f"{name} with skills {skills} and {exp} months exp. Worked on ML projects."
    return [sid, name, loc, skills, exp, edu, resume_text, '', 'NA']
with open('data/sample_cvs.csv','w',newline='') as f:
    w = csv.writer(f)
    w.writerow(['id','name','location','skills','experience_months','education','resume_text','social_links','national_id_masked'])
    for i in range(1,41):
        w.writerow(make_cv(i))
with open('data/sample_jds.csv','w',newline='') as f:
    w = csv.writer(f)
    w.writerow(['id','title','location','required_skills','description'])
    for i in range(1,9):
        skills = ','.join(random.sample(skills_pool, k=random.randint(3,6)))
        w.writerow([f'JD_{i}', f'Job_{i}', random.choice(['Mumbai','Remote','Pune']), skills, f'We are looking for skills {skills}'])
with open('data/sample_feedbacks.csv','w',newline='') as f:
    w = csv.writer(f)
    w.writerow(['candidate_id','reviewer_role','feedback_text','date'])
    for i in range(1,41):
        cid = f'Candidate_{i}'
        w.writerow([cid,'recruiter',random.choice(['Good communication','Average skills','Needs improvement']),'2025-08-10'])
print('Generated sample CSVs in data/ directory')
