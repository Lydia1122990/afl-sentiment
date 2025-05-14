import os
import json
import time
import praw
import redis
import requests
import nltk
from nltk.tokenize import sent_tokenize
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from elasticsearch8 import Elasticsearch

# List of keywords related to public transportation (to be provided by user)
transport_keywords = [
    "train", "trains", "tram", "trams", "bus", "buses", "metro", "subway", "shuttle", "light rail", "skybus",

    "ptv", "myki", "vline", "yarratrams", "metro trains",

    "opal",          # Sydney
    "translink",     # Brisbane
    "adelaidemetro", # Adelaide
    "act transport", # Canberra
    "perth transport",  # Perth 
    "hobart bus",    # Hobart 
    "darwinbus",     # Darwin

    "train fare", "tram fare", "bus fare", "metro fare", "vline fare", "light rail fare",
    "train ticket", "tram ticket", "bus ticket", "metro ticket", "vline ticket",

    "train delay", "tram delay", "bus delay", "vline delay",
    "train cancelled", "tram cancelled", "bus cancelled",
    "train shutdown", "tram shutdown", "rail shutdown",
    "train maintenance", "tram maintenance", "track maintenance", "signal fault",

    "train replacement", "tram replacement", "bus replacement", "replacement bus",
    "train trackwork", "tram trackwork", "bus trackwork",
    "train service change", "tram service change", "bus service change",
    "train no service", "tram no service", "bus no service",
    "train diversion", "tram diversion", "bus diversion",
    "train engineering works", "tram engineering works", "bus engineering works",
    "train weekend closure", "tram weekend closure", "bus weekend closure",
    "train driver shortage", "tram driver shortage", "bus driver shortage"

    "crowded train", "crowded tram", "overcrowded bus", "late train", "on time train", "train overcrowding"

    "fare evasion", "ticket evasion", "dodging fare", "fare dodger",
    "fare dodging", "evading fare", "jumping fare", "ride without ticket",
    "got caught without myki", "fare fine",
    "fined for no ticket", "didn't tap on", "forgot to tap", 
    "inspection", "ticket inspector", "ticket check", "fare compliance"

    # Melbourne
    "no myki", "myki fine", "forgot myki", "didn't tap myki",
    "myki evasion", "caught without myki"

    # Sydney
    "no opal", "opal fine", "forgot opal", "didn't tap opal",
    "opal evasion", "caught without opal"
    # Brisbane
    "no gocard", "go card fine", "forgot go card", "didn't tap go card",
    "translink fine", "caught without gocard"
    # Adelaide
    "no metrocard", "metrocard fine", "adelaide metro fine", "forgot metrocard"
    # Canberra
    "no myway", "myway fine", "didn't tap myway"
]
# List of city names (to be provided by user)
city_names = [
    "melb", "melbourne", "syd", "sydney", "bne", "brisbane", "adl", "adelaide", "perth",
    "cbr", "canberra", "hobart", "darwin"
]

def match_topic(text):
    """
    Check if any keyword related to public transportation is in the text.
    """
    if not text:
        return False
    text_lower = text.lower()
    for kw in transport_keywords:
        if kw and kw.lower() in text_lower:
            return True
    return False

def city_contain(text):
    """
    Check if any city name is in the text.
    Returns the first matching city name or None.
    """
    if not text:
        return None
    text_lower = text.lower()
    for city in city_names:
        if city and city.lower() in text_lower:
            return city
    return None

def clean_text(text):
    """
    Use the Fission text-clean microservice to clean the text.
    """
    try:
        res = requests.post("http://router.fission/text-clean", json={"text": text})
        if res.status_code == 200:
            result = res.json()
            return result.get("text", "")
    except Exception as e:
        print(f"Text-clean service error: {e}")
    return text

def analyze_text(text, analyzer):
    """
    Analyze the sentiment of the text using VADER on a sentence basis.
    Returns the average compound sentiment score.
    """
    if not text:
        return 0.0
    sentences = sent_tokenize(text)
    if not sentences:
        return 0.0
    score_sum = 0.0
    for sentence in sentences:
        vs = analyzer.polarity_scores(sentence)
        score_sum += vs["compound"]
    return score_sum / len(sentences)

def process_submission(submission, task_team, es, analyzer):
    """
    Process a single Reddit submission (post):
    - Clean text, check topic/city relevance
    - Calculate sentiment score
    - Store result in Elasticsearch
    - Process comments similarly
    """
    # Prepare content text (title + body for posts)
    text = ""
    if getattr(submission, "title", ""):
        text = submission.title + " "
    if getattr(submission, "selftext", ""):
        text += submission.selftext

    cleaned_text = clean_text(text)
    # Check if relevant
    has_topic = match_topic(cleaned_text)
    has_city = city_contain(cleaned_text) is not None

    if not has_topic and not has_city:
        # Skip if not relevant to public transportation
        return

    # Compute sentiment for the post
    sentiment_score = analyze_text(cleaned_text, analyzer)

    # Determine city for this document
    city_name = city_contain(cleaned_text)
    if not city_name:
        # If not found in text, use task team if it's a specific city (and not 'publictransport')
        if task_team.lower() != "publictransport":
            city_name = task_team
        else:
            city_name = ""

    # Prepare document for Elasticsearch
    post_doc = {
        "type": "post",
        "platform": "Reddit",
        "city": city_name,
        "sentiment": sentiment_score,
        "text": cleaned_text,
        "upvote": submission.score,
        "createdOn": int(submission.created_utc),
        "url": f"https://reddit.com{submission.permalink}",
        "docId": submission.id
    }
    es.index(index="public-transport-sentiment", body=post_doc)

    # Process comments of the submission
    try:
        submission.comments.replace_more(limit=None)
    except Exception:
        pass
    for comment in submission.comments.list():
        comment_text = getattr(comment, "body", "")
        if not comment_text:
            continue
        cleaned_comment = clean_text(comment_text)
        has_topic_c = match_topic(cleaned_comment)
        has_city_c = city_contain(cleaned_comment) is not None
        if not has_topic_c and not has_city_c:
            continue
        sentiment_score_c = analyze_text(cleaned_comment, analyzer)
        city_name_c = city_contain(cleaned_comment)
        if not city_name_c:
            if task_team.lower() != "publictransport":
                city_name_c = task_team
            else:
                city_name_c = ""
        comment_doc = {
            "type": "comment",
            "platform": "Reddit",
            "city": city_name_c,
            "sentiment": sentiment_score_c,
            "text": cleaned_comment,
            "upvote": comment.score,
            "createdOn": int(comment.created_utc),
            "url": f"https://reddit.com{comment.permalink}",
            "docId": comment.id
        }
        es.index(index="public-transport-sentiment", body=comment_doc)

def main():
    nltk.download('punkt')

    # Initialize Redis (adjust host/port as needed)
    redis_host = os.environ.get("REDIS_HOST", "redis")
    redis_port = int(os.environ.get("REDIS_PORT", 6379))
    r = redis.Redis(host=redis_host, port=redis_port, db=0)

    # Initialize Elasticsearch (adjust host/port as needed)
    es_host = os.environ.get("ELASTICSEARCH_HOST", "elasticsearch")
    es_port = int(os.environ.get("ELASTICSEARCH_PORT", 9200))
    es = Elasticsearch(f"http://{es_host}:{es_port}")

    # Initialize Reddit API (set your credentials via environment variables)
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "public-transport-sentiment")
    )

    # Initialize VADER sentiment analyzer
    analyzer = SentimentIntensityAnalyzer()

    queue_name = "trans:subreddit"
    while True:
        task_data = r.lpop(queue_name)
        if not task_data:
            time.sleep(5)
            continue

        try:
            task = json.loads(task_data)
        except json.JSONDecodeError:
            continue

        task_team = task.get("team", "")
        limit = task.get("limit", 10)

        # Determine subreddit name from task_team
        subreddit_name = task_team
        if not subreddit_name:
            continue

        try:
            subreddit = reddit.subreddit(subreddit_name)
            for submission in subreddit.new(limit=limit):
                process_submission(submission, task_team, es, analyzer)
        except Exception as e:
            print(f"Error processing subreddit {subreddit_name}: {e}")


