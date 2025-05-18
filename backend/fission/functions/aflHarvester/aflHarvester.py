import praw 
from praw.reddit import Subreddit
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer 
from elasticsearch8 import Elasticsearch, exceptions,ApiError  
from datetime import datetime
import nltk
nltk.download('punkt_tab') 
from nltk.tokenize import sent_tokenize
import requests  
import json
import redis 
from flask import current_app 


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
        "westernbulldogs":["western bulldogs","dogs", "doggies", "scraggers", "the scray", "footscray", "tricolours"]}

# map nickname to team name
teamNickname = {}
for team, nicknames in TEAM.items():
    for alias in nicknames:
        teamNickname[alias.lower()] = team


def cleanText(text)  -> str:
    """
    Send text to fission fucntion text-clean for cleaning and return cleaned text
    """
    url='http://router.fission/text-clean'
    payload = {"text":text}
    response = requests.post(url,json=payload)
    return response.json()["cleanedText"]


def addElastic(docID,indexText,doc):
    """
    Send data to fission function addelastic to store into elastic
    """ 
    url='http://router.fission/addelastic'
    payload = {"indexDocument":indexText,"docID":docID,"doc":doc}  
    try:
        response = requests.post(url, json=payload, timeout=5)
        current_app.logger.info(f'=== aflHarvester: AddElastic response: {response.status_code} {response.text} ===')  
    except Exception as e:
        current_app.logger.info(f'=== aflHarvester: Exception in addElastic POST: {str(e)} ===')   
     
    return "ok"

def checkPost(docID,indexDoc):
    """
    Check post ID see if exist in elastic index
    """
    url='http://router.fission/checkelastic'
    payload = {
            "indexDocument": indexDoc,
            "docID": docID, 
        }
    res = requests.post(url,json=payload) 
    return res.json()["found"]

def teamMentioned(text, teams=teamNickname)  -> list:
    """
    Found team mentioned in the team
    """
    foundTeam = set() 
    for nickname, team in teams.items():
        if nickname in text.lower():
            foundTeam.add(team)
    return list(foundTeam)

def sentimentPerTeam(text,postSub, upvoteScore=1, teams=TEAM) -> dict:
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
            # weighted avg sentment where theres more than one sentiment v alue total sentiment / upvote*number of sentence that match team
            resultSentiment[team] = round(sum(sentiments) / (abs(upvoteScore) * len(sentiments)), 3)
        else:
            resultSentiment[team] = 0.0
        
    return resultSentiment 

def storeElastic(text,post,postType,sentiments, teamsBool,commentID=False)  -> str:
    """
    store data into elastic, docid base on its comment ID and post ID, if post does not mention team then consider subreddit team 
    """
    try:
        if teamsBool:
            for team,sentiment in sentiments.items(): 
                docId = (f"{commentID}_{team}_comment " if commentID else  f"{post.id}_{team}_{postType}").lower() 
                
                if checkPost(docId,"afl-testing"):
                    current_app.logger.info(
                        f'Skipped {docId} as it exists ' 
                    )
                    return "exist"
                current_app.logger.info(
                    f'Processing {docId} successful' 
                ) 
                doc = {"type": postType,
                       "platform":"Reddit",                       
                      "team": team.lower(),
                      "sentiment":sentiment,
                      "text": text,
                      "upvote":post.score,
                      "createdOn": datetime.fromtimestamp(post.created_utc).isoformat(),
                      "url":post.url,
                }
                addElastic(docId,"afl-sentiment",doc) 
                current_app.logger.info(
                    f'Stored {docId} successful' 
                ) 
        else: 
            docId = (f"{commentID}_{post.subreddit.display_name.lower()}_comment " if commentID else  f"{post.id}_{post.subreddit.display_name.lower()}_{postType}").lower() 
            if checkPost(docId,"afl-testing"):
                current_app.logger.info(
                    f'Skipped {docId} as it exists ' 
                )
                return "exist"
            current_app.logger.info(
                        f'Storing {docId}' 
                    )
            doc = {"type": postType,
                   "platform":"Reddit",  
                      "team": post.subreddit.display_name.lower(),
                      "sentiment":sentiments,
                      "text": text,
                      "upvote":post.score,
                      "createdOn": datetime.fromtimestamp(post.created_utc).isoformat(),
                      "url":post.url,
                }   
            addElastic(docId,"afl-sentiment",doc)
            current_app.logger.info(
                    f'Stored {docId} successful' 
                ) 
        return "ok"
    except ApiError as e:
        current_app.logger.info(f'=== aflHarvester: {e} occur when processing {post.id}_{post.subreddit.display_name.lower()} ===') 
        return "ok"
   

def harvestSubreddit(redditTeam, postLimits=10) -> str:
    """
    Harvest post and its comments and get the sentiment value
    Fetch new posts each run. Check if post exist in index if it does break function early and move next.
    """ 
    current_app.logger.info(f'=== aflHarvester: Initialise Reddit ===')
    with open("/secrets/default/elastic-secret/REDDIT_CLIENT_ID") as f:
        clientID = f.read().strip()

    with open("/secrets/default/elastic-secret/REDDIT_CLIENT_SECRET") as f:
        clientSecret = f.read().strip() 
    reddit = praw.Reddit(
        client_id=clientID,
        client_secret=clientSecret,
        user_agent="python:reddit-harvester:v1.0 (by /u/Exact_Agency_3144)",
    )
    subreddit = reddit.subreddit(redditTeam)  
    current_app.logger.info(f'=== aflHarvester: Process reddit post/comments ===')
    for post in subreddit.new(limit=postLimits): 
        print(post.url) 
        text = cleanText(post.title + " " + post.selftext)
        postTeams = teamMentioned(text)

        if postTeams:
            sentiment = sentimentPerTeam(text,post.subreddit.display_name.lower(),post.score, postTeams) 
            stored = storeElastic(text,post,"post",sentiment,True)
            if stored == "exist":
                break
        else: 
            sentiment =  sentimentAnalyser.polarity_scores(text)['compound'] 
            stored = storeElastic(text,post,"post",sentiment,False)
            if stored == "exist":
                break
            
            
        post.comments.replace_more(limit=0) 
        
        for comment in post.comments.list():
            commentText = cleanText(comment.body)
            commentTeams = teamMentioned(commentText)
            # Skip if it's reply to another comment AND doesn't mention a team
            if comment.parent_id.startswith("t1_") and not commentTeams:
                continue 
            if commentTeams: 
                sentiment = sentimentPerTeam(commentText,post.subreddit.display_name.lower(), comment.score, commentTeams)
                storeElastic(commentText,post,"comment",sentiment,True,comment.id) 
    return "ok"
        
        


def main():
    """
    Run harvest subreddit for all AFL team, skip if we get an conflicterror
    Return: return string and 200 code after harvested afl data
    """
    current_app.logger.info(f'=== aflHarvester: Initialise ===') 
    redisClient: redis.StrictRedis = redis.StrictRedis(
        host='redis-headless.redis.svc.cluster.local',
        socket_connect_timeout=5,
        decode_responses=False
    )  

    try:
        team = redisClient.rpop("afl:subreddit")
        if not team:
            return "Queue empty", 200
        job = json.loads(team)
        harvestSubreddit(job["team"], postLimits=job["limit"]) 
        current_app.logger.info(f'=== aflHarvester: Job completed Harvested {job["team"]} ===')
        return f"Harvested {job['team']}", 200
    except ApiError as e:
        return json.dumps({"error": str(e)}), 500       