import pandas as pd
import os
print('Project root:', os.getcwd())
cvs = pd.read_csv(os.path.join('data','sample_cvs.csv'))
jds = pd.read_csv(os.path.join('data','sample_jds.csv'))
fb = pd.read_csv(os.path.join('data','sample_feedbacks.csv'))
print('CVs:', len(cvs), 'JDs:', len(jds), 'Feedbacks:', len(fb))
