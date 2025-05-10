import praw 
from praw.reddit import Subreddit
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer 
from elasticsearch8 import Elasticsearch, exceptions,ApiError 

import os
from datetime import datetime
from dotenv import load_dotenv 
import nltk
nltk.download('punkt_tab') 
from nltk.tokenize import sent_tokenize
import requests 
from flask import request
import json

# load_dotenv()
# reddit auth

# fission package create --spec --name aflharvester-pkg --source ./functions/aflHarvester/aflHarvester.py --source ./functions/aflHarvester/requirements.txt --env python39 
# fission fn create --spec --name aflharvester --pkg aflharvester-pkg --env python39 --entrypoint aflHarvester.main --specializationtimeout 180 --secret elastic-secret
# fission route create --spec --name afl-harvester-route --function aflharvester --url /aflharvester --method POST

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


def cleanText(text):
    """
    Send text to fission fucntion text-clean for cleaning and return cleaned text
    """
    url='http://textclean.default.svc.cluster.local:9090/text-clean'
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
    """
    store data into elastic, docid base on its comment ID and post ID, if post does not mention team then consdier subreddit team 
    """
    try:
        count = 0 
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
                print(json.dumps(doc,indent=4,sort_keys=True))
        else:
            count += 1
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
            # print(f"added {count} {docId} {post.subreddit.display_name.lower()}")
            print(json.dumps(doc,indent=4,sort_keys=True))
        return "ok"
    except exceptions.ConflictError:
        print(f"Document {post.id}_{team} already exists, skipping...")
        return "ok"
        
 
def harvestSubreddit(redditTeam, postLimits=10):
    """
    Harvest post and its comments and get the sentiment value
    """ 
    with open("/secrets/default/elastic-secret/REDDIT_CLIENT_ID") as f:
        clientID = f.read().strip()

    with open("/secrets/default/elastic-secret/REDDIT_CLIENT_SECRET") as f:
        clientSecret = f.read().strip() 
    # clientID="9Jl_BASawbGZY2j72z96wg"
    # clientSecret="DmsapmngWtzjfke4jhJhNOcVgkUf8w"
    reddit = praw.Reddit(
        client_id=clientID,
        client_secret=clientSecret,
        user_agent="python:reddit-harvester:v1.0 (by /u/Exact_Agency_3144)",
    )
    subreddit = reddit.subreddit(redditTeam)
    
    for post in subreddit.new(limit=postLimits): 
        print(post.title + " " + post.selftext)
        print(post.url)
        text = cleanText(post.title + " " + post.selftext).replace('\u2019',"'").replace('\n', ' ').replace('\"',"").replace("\u00a0","")
        postTeams = teamMentioned(text)

        if postTeams:
            sentiment = sentimentPerTeam(text,post.subreddit.display_name.lower(),post.score, postTeams) 
            storeElastic(text,post,"post",sentiment,True)
        else: 
            sentiment =  sentimentAnalyser.polarity_scores(text)['compound']  
            storeElastic(text,post,"post",sentiment,False)
            
        post.comments.replace_more(limit=0) 
        
        for comment in post.comments.list():
            commentText = cleanText(comment.body).replace('\u2019',"'").replace('\n', ' ').replace('\"',"").replace("\u00a0","").replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2014', "-").replace('\u00a0', " ").replace('\u2026', "...")
            commentTeams = teamMentioned(commentText)
            # Skip if it's reply to another comment AND doesn't mention a team
            if comment.parent_id.startswith("t1_") and not commentTeams:
                continue 
            if commentTeams: 
                sentiment = sentimentPerTeam(commentText,post.subreddit.display_name.lower(), comment.score, commentTeams)
                storeElastic(commentText,post,"comment",sentiment,True,comment.id)

def initalCheck(es, team):
    """
    Check if the team has already been harvested (by looking for any doc with team), if not then return false and set limit to 10 for active scrape
    """
    try:
        query = {
            "query": {
                "term": {
                    "team.keyword": team
                }
            }
        }
        resp = es.search(index="afl-sentiment", body=query, size=1)
        return resp['hits']['total']['value'] > 0
    except ApiError as e:
        print(f"Error checking harvest status for {team}: {e}", flush=True)
        return False

def main():
    """
    Run harvest subreddit for all AFL team, skip if we get an error
    """
    print("🔥 main() function started", flush=True) 
    with open("/secrets/default/elastic-secret/ES_USERNAME") as f:
        es_username = f.read().strip()

    with open("/secrets/default/elastic-secret/ES_PASSWORD") as f:
        es_password = f.read().strip() 
    # es_username = "elastic"
    # es_password = "aeyi9Ok7raengoNgahlaK4neoghooz8O"
    # "" 
    es = Elasticsearch(
    hosts=["https://elasticsearch-master.elastic.svc.cluster.local:9200"],
    basic_auth=(es_username, es_password),verify_certs=False,ssl_show_warn=False) 
    print(f"✅ Retrieved secrets: {es_username} {es_password}", flush=True)


    try:
        print("🔄 Running initial team check...", flush=True)
        limit = 1000 # fixed inital post per subreddit
        for team in TEAM.keys():
            print(f"Checking team: {team}", flush=True)
            if not initalCheck(es, team):
                print(f"Team {team} not harvested yet", flush=True)
                continue
            else:
                print(f"Team {team} already harvested", flush=True)
                limit = 10
                break 
        for i in TEAM.keys():
            print(f"📦 Harvesting subreddit for: {i} with limit {limit}", flush=True)  # ✅ Step 5
            try:
                harvestSubreddit(i,postLimits=limit)
            except Exception as e:
                print(f"Skipping {i} due to error: {e}", flush=True) 
                continue 
        print("✅ Completed harvesting", flush=True)
        return "ok",200
    except ApiError as e:
        return json.dumps({"error": str(e)}), 500
    
    # return "ok", 200
    
    # for i in TEAM.keys():
    #     try:
    #         harvestSubreddit(i,postLimits=1000)
    #     except Exception as e:
    #         print(f"Skipping {i} due to error: {e}")
    #         continue
    
        






main()
