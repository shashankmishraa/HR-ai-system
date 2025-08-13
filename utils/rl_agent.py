# utils/rl_agent.py
import os, math, random, pickle, glob
from datetime import datetime
from collections import defaultdict

# ------------------------------
# Actions (order matters for Q)
# ------------------------------
ACTIONS = ["HIRE", "REJECT", "ASSIGN_TASK", "HOLD"]
A2I = {a:i for i,a in enumerate(ACTIONS)}
I2A = {i:a for a,i in A2I.items()}

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")

# ------------------------------
# Feature helpers
# ------------------------------

def _norm_sentiment(val):
    """
    Accepts sentiment either in [-1,1] or [0,1]. Returns [0,1].
    """
    if val is None:
        return 0.5
    try:
        v = float(val)
    except:
        return 0.5
    # If it looks like [-1,1], map to [0,1]
    if v < 0.0:
        return max(0.0, min(1.0, (v + 1.0)/2.0))
    # Else assume already [0,1]
    return max(0.0, min(1.0, v))

def _bin_match_score(ms):
    # ms in [0,1] -> 10 bins (0..9)
    try:
        v = float(ms)
    except:
        v = 0.0
    v = max(0.0, min(1.0, v))
    return int(min(9, math.floor(v * 10)))

def _bin_sentiment(s):
    # s in [0,1] -> 5 bins (0..4)
    v = _norm_sentiment(s)
    return int(min(4, math.floor(v * 5)))

def _bin_experience(exp_months):
    try:
        e = int(exp_months)
    except:
        e = 0
    if e <= 12:  return 0
    if e <= 36:  return 1
    if e <= 72:  return 2
    return 3

def _loc_flag(loc_match):
    return 1 if bool(loc_match) else 0

def _prev_action_id(prev_action):
    if prev_action in A2I: 
        return A2I[prev_action]
    # default "REJECT" as previous
    return A2I["REJECT"]

def features_from_eval(eval_result):
    """
    Map /evaluate() result to a feature dict for RL.
    """
    ms   = eval_result.get("match_score", eval_result.get("similarity", 0.0))
    sent = eval_result.get("sentiment", 0.0)
    exp  = eval_result.get("cv_meta", {}).get("experience_months", eval_result.get("experience_months", 0))
    loc  = eval_result.get("location_match")
    if loc is None:
        # fallback from meta locations if present
        cv_loc = (eval_result.get("cv_meta") or {}).get("location")
        jd_loc = (eval_result.get("jd_meta") or {}).get("location")
        loc = (cv_loc and jd_loc and str(cv_loc).strip().lower() == str(jd_loc).strip().lower())

    return {
        "match_score": float(ms) if ms is not None else 0.0,
        "sentiment": _norm_sentiment(sent),
        "experience_months": int(exp) if exp is not None else 0,
        "location_match": bool(loc),
        "prev_action": eval_result.get("prev_action", "REJECT")
    }

def featurize(feats):
    """
    Convert feature dict to a discrete state for Q-table.
    State: (m_bin, s_bin, e_bin, loc, prev_id)
    """
    m_bin = _bin_match_score(feats.get("match_score", 0.0))
    s_bin = _bin_sentiment(feats.get("sentiment", 0.5))
    e_bin = _bin_experience(feats.get("experience_months", 0))
    loc   = _loc_flag(feats.get("location_match", False))
    prev  = _prev_action_id(feats.get("prev_action", "REJECT"))
    return (m_bin, s_bin, e_bin, loc, prev)

# ------------------------------
# Q-table utilities
# ------------------------------

def new_q_table():
    # defaultdict: unseen state -> zero vector
    return defaultdict(lambda: [0.0 for _ in ACTIONS])

def latest_q_path():
    if not os.path.isdir(MODELS_DIR):
        return None
    files = sorted(glob.glob(os.path.join(MODELS_DIR, "q_table_*.pkl")))
    return files[-1] if files else None

def save_q_table(Q, path=None):
    if not os.path.isdir(MODELS_DIR):
        os.makedirs(MODELS_DIR, exist_ok=True)
    if path is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(MODELS_DIR, f"q_table_{stamp}.pkl")
    with open(path, "wb") as f:
        pickle.dump(dict(Q), f)  # cast to dict for compactness
    return path

def load_q_table(path=None):
    if path is None:
        path = latest_q_path()
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        raw = pickle.load(f)
    Q = new_q_table()
    for k,v in raw.items():
        Q[k] = v
    return Q

# ------------------------------
# Environment + Training
# ------------------------------

def _sample_state():
    """
    Draw a plausible random state for training.
    """
    ms = random.random()                # 0..1
    sent = random.uniform(0.0, 1.0)     # 0..1
    exp = random.choice([6, 18, 30, 48, 84, 120])  # buckets
    loc = random.random() < 0.55        # ~55% location match
    prev = random.choice(ACTIONS)
    return featurize({
        "match_score": ms,
        "sentiment": sent,
        "experience_months": exp,
        "location_match": loc,
        "prev_action": prev
    })

def _exp_norm(e_bin):
    # 0,1,2,3 -> 0.15, 0.45, 0.7, 0.9 (rough calibration)
    return [0.15, 0.45, 0.70, 0.90][int(e_bin)]

def _state_to_continuous(state):
    m_bin, s_bin, e_bin, loc, _ = state
    m = (m_bin + 0.5)/10.0         # center of the bin
    s = (s_bin + 0.5)/5.0
    e = _exp_norm(e_bin)
    l = 1.0 if loc else 0.0
    return m, s, e, l

def _simulate_reward(state, action_idx):
    """
    Simulate an outcome -> reward based on PDF spec heuristics.
    """
    m, s, e, l = _state_to_continuous(state)
    # performance proxy (0..1)
    perf = max(0.0, min(1.0, 0.6*m + 0.2*s + 0.15*e + 0.05*l + random.uniform(-0.03, 0.03)))

    a = I2A[action_idx]
    if a == "HIRE":
        if perf >= 0.70:    return 1.0 + (0.1 if s > 0.5 else 0.0)
        if perf <= 0.40:    return -1.0
        return 0.1 if m > 0.65 else -0.1

    if a == "REJECT":
        if perf < 0.40:     return 0.5
        if perf >= 0.70:    return -0.6
        return -0.05

    if a == "ASSIGN_TASK":
        # chance of task success rises with m & e
        p_succ = 0.25 + 0.5*m + 0.15*e + 0.1*l
        p_succ = max(0.0, min(1.0, p_succ))
        return 0.6 if (random.random() < p_succ) else -0.4

    if a == "HOLD":
        return -0.05

    return 0.0

def _epsilon_greedy(Q, state, epsilon):
    # Explore
    if random.random() < epsilon:
        return random.randrange(len(ACTIONS))
    # Exploit
    values = Q[state]
    best = max(range(len(ACTIONS)), key=lambda i: values[i])
    return best

def train_q(episodes=2000, steps_per_episode=6, alpha=0.12, gamma=0.95,
            epsilon=1.0, epsilon_min=0.05, epsilon_decay=0.995, seed=42):
    random.seed(seed)
    Q = new_q_table()

    for _ in range(episodes):
        s = _sample_state()
        for _step in range(steps_per_episode):
            a = _epsilon_greedy(Q, s, epsilon)
            r = _simulate_reward(s, a)
            s_next = _sample_state()
            # Q-learning update
            q_sa = Q[s][a]
            max_next = max(Q[s_next])
            Q[s][a] = q_sa + alpha * (r + gamma*max_next - q_sa)
            s = s_next
        if epsilon > epsilon_min:
            epsilon *= epsilon_decay
    return Q

# ------------------------------
# Inference
# ------------------------------

def decide_action(eval_result, Q=None, prev_action="REJECT"):
    """
    Given the /evaluate() output dict, return an RL decision.
    Fallback to a simple rule if Q is None.
    """
    feats = features_from_eval(eval_result)
    feats["prev_action"] = prev_action
    state = featurize(feats)

    if Q is None:
        # rule fallback
        ms = feats["match_score"]
        loc = feats["location_match"]
        if loc and ms >= 0.80:
            return "HIRE"
        if ms >= 0.65:
            return "ASSIGN_TASK"
        return "REJECT"

    # otherwise, RL policy
    values = Q[state]
    best = max(range(len(ACTIONS)), key=lambda i: values[i])
    return I2A[best]
