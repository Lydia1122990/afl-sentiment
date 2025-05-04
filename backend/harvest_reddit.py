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

TEAM = {"adelaidefc":["adelaide crows","crows", "crows reserves", "whites", "white noise","kuwarna"],
        "brisbanelions":["brisbane lions","maroons", "gorillas", "lions"],
        "carltonblues":["carlton","blues","blue baggers","baggers","old navy blues"],
        "collingwoodfc":["collingwood","magpies","pies","woods","woodsmen"],
        "essendonfc":["essendon","bombers","dons","same olds"],
        "fremantlefc":["fremantle","dockers","freo","walyalup"], 
        "geelongcats":["geelong","cats"],
        "gcfc":["gold coast suns","suns","sunnies","coasters"],
        "gwsgiants":["gws giants","greater western sydney giants","giants","gws","orange team"],
        "hawktalk":["hawthorn","hawks"],
        "melbournefc":["melbourne","demons","dees","narrm","redlegs","fuchsias"],
        "northmelbournefc":["north melbourne","kangaroos","kangas","roos","north","shinboners"],
        "weareportadelaide":["port adelaide","power","port","cockledivers", "seaside men", "seasiders", "magentas", "portonians", "ports"],
        "richmondfc":["richmond","tigers", "tiges", "fighting fury"],
        "stkilda":["st kilda","saints","sainters"],
        "sydneyswans":["sydney swans","swans","swannies", "bloods"],
        "westcoasteagles":["west coast eagles","eagles"],
        "westernbulldogs":["western bulldogs","dogs", "doggies", "scraggers", "the scray", "footscray", "tricolours"],
        "tasmanianafl":["tasmania football club","devils", "tassie"]}
# map nickname to team name
teamNickname = {}
for team, nicknames in TEAM.items():
    for alias in nicknames:
        teamNickname[alias.lower()] = team


def cleanEmoji(text):
    
    """
    Remove emoji and return text
    task: might need to edit vadot text to read emoji
    """ 
    return emoji.demojize(text).replace("::"," ").replace(":","").replace("_"," ")

def teamMentioned(text, teams=teamNickname):
    """
    Found team mentioned in the team
    """
    foundTeam = set()
    for nickname, team in teams.items():
        if nickname in text.lower():
            foundTeam.add(team)
    return list(foundTeam)

def sentimentPerTeam(text,upvoteScore=1, teams=TEAM):
    """
    Get sentiment per team, if team is not mentioned in posts then assumed its related to subredit team
    """
    sentences = sent_tokenize(text)
    teamSentiment = {team: [] for team in TEAM}
    
    for sentence in sentences:
        score = sentimentAnalyser.polarity_scores(sentence)['compound']
        for team, nicknames in TEAM.items():
            teamFound = any(nickname in sentence.lower() for nickname in nicknames)
            if teamFound:
                
                teamSentiment[team].append(score * abs(upvoteScore)) 
    resultSentiment = {}
    for team,scores in teamSentiment.items():
        if scores:
            resultSentiment[team] = round(sum(scores) / sum([abs(upvoteScore)] * len(scores)), 3)
        elif any(nickname in text.lower() for nickname in TEAM[team]):
                score = sentimentAnalyser.polarity_scores(text)['compound']
                resultSentiment[team] = round(score * abs(upvoteScore), 3)
    # Aggregate average score per team 
    return resultSentiment 
 
def harvestSubreddit(subreddit, postLimits=10):
    """
    Harvest post and its comments and get the sentiment value
    """ 
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent="python:reddit-harvester:v1.0 (by /u/Exact_Agency_3144)",
    )
    subreddit = reddit.subreddit(subreddit)

    for post in subreddit.new(limit=postLimits): 
        text = cleanEmoji(post.title + " " + post.selftext)
        postTeams = teamMentioned(text)
        
        if postTeams:
            sentiment = sentimentPerTeam(text,post.score, postTeams)
            print(f"teamMentioned: {postTeams}")
            print(f"text: {text}")
            print(f"[POST SENTIMENT] {sentiment}")
        else: 
            sentiment =  sentimentAnalyser.polarity_scores(text)['compound']
            print(f"[POST SENTIMENT] {sentiment}")
            
        post.comments.replace_more(limit=0) 

        for comment in post.comments.list():
            commentText = cleanEmoji(comment.body)
            # Skip if it's reply to another comment AND doesn't mention a team
            if comment.parent_id.startswith("t1_") and not teamMentioned(comment.body):
                continue
            mentioned = teamMentioned(commentText) 
            if mentioned:
                score = sentimentPerTeam(commentText,comment.score)
                print(f"Comment (Score: {comment.score}): {score} \n-> {comment.body}\n")

harvestSubreddit("StKilda",postLimits=5)
# es_password = os.getenv("ES_PASSWORD")
# es_username = os.getenv("ES_USERNAME")
# es = Elasticsearch(
#     hosts=["https://localhost:9200"],
#     basic_auth=(es_username, es_password),
#     verify_certs=False,
# )







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
