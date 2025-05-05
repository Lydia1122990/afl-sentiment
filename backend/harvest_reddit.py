from enum import verify
import praw
from praw.models.listing.mixins import submission
from praw.reddit import Subreddit
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime
import time
from elasticsearch import Elasticsearch
import os
from dotenv import load_dotenv
import traceback

load_dotenv()
# reddit auth


reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="python:reddit-harvester:v1.0 (by /u/Exact_Agency_3144)",
)


es_password = os.getenv("ES_PASSWORD")
es_username = os.getenv("ES_USERNAME")
es = Elasticsearch(
    hosts=["http://localhost:9200"],
    basic_auth=(es_username, es_password),
    verify_certs=False,
)

subreddit_prefix = [
    "melbourne",
    "perth",
    "sydney",
    "brisbane",
    "adelaide",
    "canberra",
    "hobart",
    "darwin",
]

sentimentAnalyser = SentimentIntensityAnalyzer()


def process_post(posts, subreddit):
    try:
        text = f"{posts.title or ''} {posts.selftext or ''}".lower()
        found_city = next((city for city in subreddit_prefix if city in text), None)
        if found_city == subreddit:
            sentiment = sentimentAnalyser.polarity_scores(
                posts.title + " " + posts.selftext
            )["compound"]
            doc = {
                "platform": "Reddit",
                "city": subreddit,
                "title": posts.title,
                "selftext": posts.selftext,
                "url": posts.url,
                "created_utc": posts.created_utc,
                "score": posts.score,
                "subreddit": subreddit,
                "sentiment": sentiment,
            }
            print("found but run before index")
            es.index(index="reddit-posts", id=posts.id, document=doc)
            print("found and ran after index")
            print(f"Indexed:{subreddit} | {posts.title}")
    except Exception as e:
        print(f"Error processsing submission: {e}")


if __name__ == "__main__":
    for city in subreddit_prefix:
        print(f"harvesting from r{city}")
        subreddit = reddit.subreddit(city)
        try:
            for sub in subreddit.new(limit=5):
                process_post(sub, city)
                time.sleep(1.5)

                print(reddit.auth.limits)
        except Exception as e:
            traceback.print_exc()
            time.sleep(0.5)
    print("harvest compelete")
