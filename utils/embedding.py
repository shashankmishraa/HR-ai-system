import numpy as np
try:
    from sentence_transformers import SentenceTransformer
    _SENTENCE_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    HAS_SBT = True
except Exception:
    HAS_SBT = False
    _SENTENCE_MODEL = None
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
def embed_corpus(list_a, list_b):
    texts = list(list_a) + list(list_b)
    if HAS_SBT:
        emb = _SENTENCE_MODEL.encode(texts, show_progress_bar=False)
        emb = np.array(emb)
        return emb[:len(list_a)], emb[len(list_a):]
    else:
        vect = TfidfVectorizer(max_features=5000, stop_words='english')
        X = vect.fit_transform(texts)
        svd = TruncatedSVD(n_components=128, random_state=42)
        X2 = svd.fit_transform(X)
        return X2[:len(list_a)], X2[len(list_a):]
