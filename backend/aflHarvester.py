import praw
from praw.models.listing.mixins import submission
from praw.reddit import Subreddit
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer 
from elasticsearch import Elasticsearch, exceptions
import os
from datetime import datetime
from dotenv import load_dotenv 
import nltk
nltk.download('punkt_tab')
import emoji
from nltk.tokenize import sent_tokenize
import requests
import json
import certifi

load_dotenv()
# reddit auth

sentimentAnalyser = SentimentIntensityAnalyzer()

TEAM = {"adelaidefc":["adelaide crows","crows", "crows reserves", "whites", "white noise","kuwarna"],
        "brisbanelions":["brisbane lions","maroons", "gorillas", "lions"],
        "CarltonBlues":["carlton","blues","blue baggers","baggers","old navy blues"],
        "collingwoodfc":["collingwood","magpies","pies","woods","woodsmen"],
        "EssendonFC":["essendon","bombers","dons","same olds"],
        "FremantleFC":["fremantle","dockers","freo","walyalup"], 
        "GeelongCats":["geelong","cats"],
        "gcfc":["gold coast suns","suns","sunnies","coasters"],
        "GWSgiants":["gws giants","greater western sydney giants","giants","gws","orange team"],
        "hawktalk":["hawthorn","hawks"],
        "melbournefc":["melbourne","demons","dees","narrm","redlegs","fuchsias"],
        "NorthMelbourneFC":["north melbourne","kangaroos","kangas","roos","north","shinboners"],
        "weareportadelaide":["port adelaide","power","port","cockledivers", "seaside men", "seasiders", "magentas", "portonians", "ports"],
        "RichmondFC":["richmond","tigers", "tiges", "fighting fury"],
        "StKilda":["st kilda","saints","sainters"],
        "sydneyswans":["sydney swans","swans","swannies", "bloods"],
        "westcoasteagles":["west coast eagles","eagles"],
        "westernbulldogs":["western bulldogs","dogs", "doggies", "scraggers", "the scray", "footscray", "tricolours"],
        "TasmanianAFL":["tasmania football club","devils", "tassie"]}
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

def cleanText(text):
    """
    Send text to fission fucntion text-clean for cleaning and return cleaned text
    """
    url='http://localhost:8888/text-clean'
    payload = {"text":text}
    response = requests.post(url,json=payload)
    return response.json()["cleanedText"]


def teamMentioned(text, teams=teamNickname):
    """
    Found team mentioned in the team
    """
    foundTeam = set() 
    for nickname, team in teams.items():
        if nickname in text.lower():
            foundTeam.add(team)
    return list(foundTeam)

def sentimentPerTeam(text,postSub, upvoteScore=1, teams=TEAM):
    """
    Get total weighted sentiment per team , if team is not mentioned in posts then assumed its related to subredit team
    """
    sentences = sent_tokenize(text)
    teamSentiment = {team: [] for team in teams}
    
    for sentence in sentences:
        sentiment = sentimentAnalyser.polarity_scores(sentence)['compound'] 
        for team, nicknames in TEAM.items():
            teamFound = any(nickname in sentence.lower() for nickname in nicknames)
            if teamFound:
                teamSentiment[team].append(sentiment * abs(upvoteScore)) # multiple by upvote score to get weighted sentiment
        if not teamFound:
            if postSub not in teamSentiment:
                teamSentiment[postSub] = []
            sentiment = sentimentAnalyser.polarity_scores(sentence)['compound']
            teamSentiment[postSub].append(sentiment * abs(upvoteScore))
    resultSentiment = {}
    for team,sentiments in teamSentiment.items(): 
        if sentiments and upvoteScore != 0:
            # weighted avg sentment where theres more than one sentiment v alue total sentiment / upvoet*number of sentence that match team
            resultSentiment[team] = round(sum(sentiments) / (abs(upvoteScore) * len(sentiments)), 3)
        else:
            resultSentiment[team] = 0.0
        
    return resultSentiment 

def storeElastic(text,post,postType,sentiments, teamsBool,commentID=False):
    es_password = os.getenv("ES_PASSWORD")
    es_username = os.getenv("ES_USERNAME")
    es = Elasticsearch(
    hosts=["https://localhost:9200"],
    basic_auth=(es_username, es_password),verify_certs=False,ssl_show_warn=False)
    # info = es.info()
    # print(info['version']['number'])
    try:
        
        if teamsBool:
            for team,sentiment in sentiments.items(): 
                docId = (f"{commentID}_{team}_comment " if commentID else  f"{post.id}_{team}_{postType}").lower() 
                doc = {"type": postType,
                       "platform":"Reddit",                       
                      "team": team,
                      "sentiment":sentiment,
                      "text": text,
                      "upvote":post.score,
                      "createdOn": datetime.fromtimestamp(post.created_utc).isoformat(),
                      "url":post.url,
                }
                # es.create(index="afl-sentiment", id=docId, document=doc)
                print(f"added {docId} {post.subreddit.display_name.lower()}")
        else:
            docId = (f"{commentID}_{post.subreddit.display_name.lower()}_comment " if commentID else  f"{post.id}_{post.subreddit.display_name.lower()}_{postType}").lower() 
            doc = {"type": postType,
                   "platform":"Reddit",  
                      "team": post.subreddit.display_name.lower(),
                      "sentiment":sentiments,
                      "text": text,
                      "upvote":post.score,
                      "createdOn": datetime.fromtimestamp(post.created_utc).isoformat(),
                      "url":post.url,
                }  
            # es.create(index="afl-sentiment", id=docId, document=doc)
            print(f"added {docId} {post.subreddit.display_name.lower()}")
        # print(json.dumps(doc,indent=4,sort_keys=True))
        return "ok"
    except exceptions.ConflictError:
        print(f"Document {post.id}_{team} already exists, skipping...")
        return "ok"
        
 
def harvestSubreddit(redditTeam, postLimits=10):
    """
    Harvest post and its comments and get the sentiment value
    """ 
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent="python:reddit-harvester:v1.0 (by /u/Exact_Agency_3144)",
    )
    subreddit = reddit.subreddit(redditTeam)

    for post in subreddit.new(limit=postLimits): 
        text = cleanText(post.title + " " + post.selftext).replace('\u2019',"'").replace('\n', ' ').replace('\"',"").replace("\u00a0","")
        postTeams = teamMentioned(text)
        
        
        if postTeams:
            sentiment = sentimentPerTeam(text,post.subreddit.display_name.lower(),post.score, postTeams) 
            storeElastic(text,post,"post",sentiment,True)
        else: 
            sentiment =  sentimentAnalyser.polarity_scores(text)['compound'] 
            # if(sentiment < 0.05):
            #     sentiment = 0.0
            storeElastic(text,post,"post",sentiment,False)
            
        post.comments.replace_more(limit=0) 
        
        for comment in post.comments.list():
            commentText = cleanText(comment.body).replace('\u2019',"'").replace('\n', ' ').replace('\"',"").replace("\u00a0","").replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2014', "-").replace('\u00a0', " ").replace('\u2026', "...")
            commentTeams = teamMentioned(commentText)
            # Skip if it's reply to another comment AND doesn't mention a team
            if comment.parent_id.startswith("t1_") and not teamMentioned(comment.body):
                continue
            mentioned = teamMentioned(commentText) 
            if mentioned: 
                sentiment = sentimentPerTeam(commentText,post.subreddit.display_name.lower(), comment.score, commentTeams)
                storeElastic(commentText,post,"comment",sentiment,True,comment.id)

def main():
    """
    Run harvest subreddit for all AFL team, skip if we get an error
    """
    for i in TEAM.keys():
        try:
            harvestSubreddit(i,postLimits=1000)
        except Exception as e:
            print(f"Skipping {i} due to error: {e}")
            continue
        
if __name__ == '__main__':    
    main()






