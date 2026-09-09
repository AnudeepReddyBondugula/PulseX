from pipeline import fetch_news
from pipeline import fetch_papers

from pipeline.summarizer import Summarizer, SummaryResult

summarizer = Summarizer()
news_articles = fetch_news.fetch_all_news()[0:5]  # Fetch the first 5 news articles

for article in news_articles:
    print(article)
    SummaryResult = summarizer.summarize_news_item(article)
    print(f"News Article ID: {SummaryResult.item_id}")
    print(f"Summary: {SummaryResult.summary}")