import requests
import praw
import os
from praw.models.listing.mixins import submission
from praw.reddit import Subreddit  
from dotenv import load_dotenv 
load_dotenv()
  

# def call_fission_clean(post: dict) -> dict:
#     response = requests.post("http://<fission-router>/clean", json=post)
#     return response.json()

# def call_fission_sentiment(cleaned_post: dict) -> dict:
#     response = requests.post("http://<fission-router>/sentiment", json=cleaned_post)
#     return response.json()

def aflHarvest(subredditName="StKilda", limit=1):
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent="python:reddit-harvester:v1.0 (by /u/Exact_Agency_3144)",
    )
    posts = reddit.subreddit(subredditName).new(limit=limit)

    for post in posts:
        uncleanedDoc = {"type": "post",
                    "platform":"Reddit",
                    "team": subredditName,
            "id": post.id,
            "title": post.title,
            "text": post.selftext,
            "sentiment":0.0,
            "upvote": post.score,
            "created_utc": post.created_utc,
            "url": post.url,
            "subreddit": post.subreddit.display_name
        }
        print(uncleanedDoc)

        # Stage 1: Clean text
        # cleaned = call_fission_clean(uncleanedDoc)

        # # Stage 2: Get sentiment
        # result = call_fission_sentiment(cleaned)

        # # Stage 3: Store in Elasticsearch
        # storeElastic(result)
aflHarvest()