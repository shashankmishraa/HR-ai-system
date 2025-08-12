from nltk.sentiment.vader import SentimentIntensityAnalyzer
import pandas as pd
sia = SentimentIntensityAnalyzer()
def sentiment_score(text):
    if not isinstance(text, str) or text.strip()=='':
        return 0.0
    s = sia.polarity_scores(text)
    return s['compound']
def process_feedbacks(feedbacks_df):
    feedbacks_df = feedbacks_df.copy()
    feedbacks_df['sentiment'] = feedbacks_df['feedback_text'].fillna('').apply(sentiment_score)
    out = feedbacks_df.groupby('candidate_id')['sentiment'].agg(['mean','count']).reset_index().rename(columns={'mean':'avg_sentiment','count':'feedback_count'})
    return out
