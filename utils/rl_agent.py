import random, pickle, os
import numpy as np
from datetime import datetime
ACTIONS = {0:'HIRE', 1:'REJECT', 2:'ASSIGN_TASK', 3:'HOLD'}
def discretize_state(sim_score, sentiment, exp_norm, loc_flag, prev_action):
    return (round(sim_score,2), round(sentiment,2), round(exp_norm,2), int(bool(loc_flag)), int(prev_action))
class SimpleEnv:
    def step(self, state):
        sim, sentiment, exp_norm, loc_flag, prev = state
        base = 0.6*sim + 0.3*exp_norm + (0.1 if loc_flag else 0)
        perf = base + random.gauss(0,0.1)
        perf = max(0.0, min(1.0, perf))
        return perf
def train_q(env=None, episodes=1000, alpha=0.1, gamma=0.95, eps=0.2):
    if env is None:
        env = SimpleEnv()
    Q = {}
    def qget(s,a): return Q.get((s,a), 0.0)
    for ep in range(episodes):
        sim_score = random.random()
        sentiment = random.uniform(-1,1)
        exp_norm = random.random()
        loc_flag = random.choice([0,1])
        prev = random.choice([0,1,2,3])
        state = discretize_state(sim_score, sentiment, exp_norm, loc_flag, prev)
        for t in range(3):
            if random.random() < eps:
                a = random.choice(list(ACTIONS.keys()))
            else:
                vals = [qget(state,act) for act in ACTIONS.keys()]
                a = int(np.argmax(vals))
            perf = env.step(state)
            if a == 0:
                if perf >= 0.7: r = 1.0
                elif perf <= 0.4: r = -1.0
                else: r = 0.0
            elif a == 2:
                r = 0.6 if perf>0.5 else -0.4
            elif a == 1:
                r = 0.5 if perf < 0.4 else -0.6
            else:
                r = -0.05
            future_vals = [qget(state,act) for act in ACTIONS.keys()]
            Q[(state,a)] = qget(state,a) + alpha*(r + gamma*max(future_vals) - qget(state,a))
    return Q
def save_q_table(Q, path=None):
    os.makedirs('models', exist_ok=True)
    if path is None:
        path = os.path.join('models', f'q_table_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pkl')
    with open(path, 'wb') as f:
        pickle.dump(Q, f)
    return path
def load_q_table(path):
    with open(path, 'rb') as f:
        return pickle.load(f)
def select_action_from_q(Q, state):
    vals = []
    for a in ACTIONS.keys():
        vals.append(Q.get((state,a), 0.0))
    best = int(np.argmax(vals))
    return best, ACTIONS[best]
