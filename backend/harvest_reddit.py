import re
import sys
import praw
from praw.models.listing.mixins import submission
from praw.reddit import Subreddit
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import time
from elasticsearch import Elasticsearch
import os
from dotenv import load_dotenv
import traceback
import nltk
nltk.download('punkt_tab')
import emoji
from nltk.tokenize import sent_tokenize


load_dotenv()
# reddit auth

sentimentAnalyser = SentimentIntensityAnalyzer()

TEAM = {"adelaide crows":1,"brisbane lions":1,"carlton":1,"collingwood":1,
           "essendon":1,"fremantle":1,"fremantle":1,"geelong":1,"gold coast suns":1,
           "gws giants":1,"hawthorn":1,"melbourne":1,"north melbourne":1,
           "port adelaide":1,"richmond":1,"st kilda":1,"sydney swans":1,
           "west coast eagles":1,"western bulldogs":1}

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="python:reddit-harvester:v1.0 (by /u/Exact_Agency_3144)",
)

def removeEmoji(text):
    
    """
    Remove emoji and return text
    task: might need to edit vadot text to read emoji
    """ 
    return emoji.demojize(text).replace("::"," ").replace(":","").replace("_"," ")

#                 posts.title + " " + posts.selftext
#             )["compound"]

def sentimentPerTeam(text, teams=TEAM):
    teamSentiment = {team: [] for team in teams}
    sentences = sent_tokenize(text)
    
    for sentence in sentences:
        score = sentimentAnalyser.polarity_scores(sentence)['compound']
        for team in teams.keys():
            if team.lower() in sentence.lower():
                teamSentiment[team].append(score)
    resultSentiment = {}
    for team,scores in teamSentiment.items():
        if scores:
            resultSentiment[team] = round(sum(scores)/len(scores),3)
    # Aggregate average score per team
    return resultSentiment 

comment = "Fremantle fan here Can I just say FUCK EEEEVEERYONE ELSE?? FUCK everyone, I can’t stand watching my team, and I’m sure you guys feel similar at times. I actually like so many of your players and fans, that I don’t even dislike Carlton anymore, like, at all. I feel filthy. I feel for you tho, even if your loss was probably about 1/3 of how embarrassing ours was. Like what is the point of watching my piss poor team and why am I going to watch them next week anyway 😭😭"
print(sentimentPerTeam(comment))


count = reddit.subreddit("AFL").subscribers
s = reddit.subreddits.popular()



# es_password = os.getenv("ES_PASSWORD")
# es_username = os.getenv("ES_USERNAME")
# es = Elasticsearch(
#     hosts=["https://localhost:9200"],
#     basic_auth=(es_username, es_password),
#     verify_certs=False,
# )

# subreddit_prefix = [
#     "melbourne",
#     "perth",
#     "sydney",
#     "brisbane",
#     "adelaide",
#     "canberra",
#     "hobart",
#     "darwin",
# ]






# def process_post(posts, subreddit):
#     try:
#         text = f"{posts.title or ''} {posts.selftext or ''}".lower()
#         found_city = next((city for city in subreddit_prefix if city in text), None)
#         if found_city == subreddit:
#             sentiment = sentimentAnalyser.polarity_scores(
#                 posts.title + " " + posts.selftext
#             )["compound"]
#             doc = {
#                 "platform": "Reddit",
#                 "city": subreddit,
#                 "title": posts.title,
#                 "selftext": posts.selftext,
#                 "url": posts.url,
#                 "created_utc": posts.created_utc,
#                 "score": posts.score,
#                 "subreddit": subreddit,
#                 "sentiment": sentiment,
#             }
#             print("found but run before index")
#             es.index(index="reddit-posts", id=posts.id, document=doc)
#             print("found and ran after index")
#             print(f"Indexed:{subreddit} | {posts.title}")
#     except Exception as e:
#         print(f"Error processsing submission: {e}")


# if __name__ == "__main__":
    
    # for city in subreddit_prefix:
    #     print(f"harvesting from r{city}")
    #     subreddit = reddit.subreddit(city)
    #     try:
    #         for sub in subreddit.new(limit=5):
    #             process_post(sub, city)
    #             time.sleep(1.5)

    #             print(reddit.auth.limits)
    #     except Exception as e:
    #         traceback.print_exc()
    #         time.sleep(0.5)
    # print("harvest compelete")
