import requests

def fetch_news_impact(symbol):
    url = f"https://newsapi.org/v2/everything?q={symbol}&apiKey=your_news_api_key"
    response = requests.get(url)
    articles = response.json().get('articles', [])
    
    # Simple sentiment analysis based on headlines
    positive_count = sum(1 for article in articles if 'positive' in article['title'].lower())
    negative_count = sum(1 for article in articles if 'negative' in article['title'].lower())
    
    if positive_count > negative_count:
        return '🟢 Positive'
    elif negative_count > positive_count:
        return '🔴 Negative'
    return '🟡 Neutral'
