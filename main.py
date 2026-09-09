from pipeline import fetch_news
from pipeline import fetch_papers

print(fetch_papers.fetch_all_papers()[0:10])