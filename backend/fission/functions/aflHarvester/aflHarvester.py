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

# fission package create --spec --name aflharvester-pkg --source ./functions/aflHarvester/aflHarvester.py --source ./functions/aflHarvester/requirements.txt --env python39 
# fission fn create --spec --name aflharvester --pkg aflharvester-pkg --env python39 --entrypoint aflHarvester.main --specializationtimeout 180 --secret elastic-secret 
# fission route create --spec --name afl-harvester-route --function aflharvester --url /aflharvester --method POST --createingress
 
# (
#     cd fission
#     fission mqtrigger create --name afl-harvesting \
#     --spec \
#     --function aflharvester \
#     --mqtype redis \
#     --mqtkind keda \
#     --topic afl \
#     --errortopic errors \
#     --maxretries 3 \
#     --metadata address=redis-headless.redis.svc.cluster.local:6379 \
#     --metadata listLength=100 \
#     --metadata listName=afl:subreddit
# )  

# fission timer create \
#   --name aflharvest-timer \
#   --spec \
#   --function aflharvester \
#   --cron "*/5 * * * *" 
  


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


def teamMentioned(text, teams=teamNickname)  -> list:
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
            # weighted avg sentment where theres more than one sentiment v alue total sentiment / upvote*number of sentence that match team
            resultSentiment[team] = round(sum(sentiments) / (abs(upvoteScore) * len(sentiments)), 3)
        else:
            resultSentiment[team] = 0.0
        
    return resultSentiment 

def storeElastic(es,text,post,postType,sentiments, teamsBool,commentID=False)  -> str:
    """
    store data into elastic, docid base on its comment ID and post ID, if post does not mention team then consdier subreddit team 
    """
    try:
        count = 0 
        if teamsBool:
            
            print("storeElastic start, flush=True")
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
                es.create(index="afl-sentiment", id=docId, document=doc)
                print(f"added {docId} {post.subreddit.display_name.lower()}", flush=True)
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
            es.create(index="afl-sentiment", id=docId, document=doc)
            print(f"added {count} {docId} {post.subreddit.display_name.lower()}", flush=True)
            print(json.dumps(doc,indent=4,sort_keys=True))
        return "ok"
    except exceptions.ConflictError:
        print(f"Document {post.id}_{post.subreddit.display_name.lower()} already exists, skipping...")
        return "ok"
    
def saveLastPost(es, subredditName, postFullname) -> str:
    """
    Store last post details into elastic database to store later
    """
    docId = f"after-{subredditName}"
    doc = {
        "type": "harvest-status",
        "platform": "Reddit",
        "team": subredditName,
        "last": postFullname,
        "updatedOn": datetime.now().isoformat()
    }
    es.index(index="harvest-details", id=docId, document=doc)
    return "ok"

def fetchLastPost(es, subredditName):
    """
    Fetch last post details
    """
    docId = f"last-{subredditName}"
    try:
        doc = es.get(index="check-storage", id=docId)
        return doc["_source"].get("last", None)
    except exceptions.NotFoundError:
        return None       
 
def harvestSubreddit(es,redditTeam, postLimits=10) -> str:
    """
    Harvest post and its comments and get the sentiment value
    Fetch new posts each run. Use after or timestamp to get the next batch. Save the latest post ID it saw. 
    keepign the code to run wihtout taking too long
    """ 
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
    
    print("fetched , flush=True")
    after = fetchLastPost(es, redditTeam) 
    
    lastPost = None
    print("fetched Done, flush=True")
    for post in subreddit.new(limit=postLimits): 
        print(post.title + " " + post.selftext)
        print(post.url)
        if after == post.fullname:
            #reach last scrapped post then break
            break
        text = cleanText(post.title + " " + post.selftext)
        postTeams = teamMentioned(text)

        if postTeams:
            sentiment = sentimentPerTeam(text,post.subreddit.display_name.lower(),post.score, postTeams) 
            storeElastic(es,text,post,"post",sentiment,True)
        else: 
            sentiment =  sentimentAnalyser.polarity_scores(text)['compound']  
            storeElastic(es,text,post,"post",sentiment,False)
            
        post.comments.replace_more(limit=0) 
        
        for comment in post.comments.list():
            commentText = cleanText(comment.body)
            commentTeams = teamMentioned(commentText)
            # Skip if it's reply to another comment AND doesn't mention a team
            if comment.parent_id.startswith("t1_") and not commentTeams:
                continue 
            if commentTeams: 
                sentiment = sentimentPerTeam(commentText,post.subreddit.display_name.lower(), comment.score, commentTeams)
                storeElastic(es,commentText,post,"comment",sentiment,True,comment.id)
        lastPost = post.fullname
    if lastPost:
        #Store last post details
        saveLastPost(es,redditTeam,lastPost)
    return "ok"
        
        


def main():
    """
    Run harvest subreddit for all AFL team, skip if we get an conflicterror
    """
    print("main() function started", flush=True) 
    with open("/secrets/default/elastic-secret/ES_USERNAME") as f:
        es_username = f.read().strip()

    with open("/secrets/default/elastic-secret/ES_PASSWORD") as f:
        es_password = f.read().strip() 
        
    redisClient: redis.StrictRedis = redis.StrictRedis(
        host='redis-headless.redis.svc.cluster.local',
        socket_connect_timeout=5,
        decode_responses=False
    ) 
    es = Elasticsearch(
    hosts=["https://elasticsearch-master.elastic.svc.cluster.local:9200"],
    basic_auth=(es_username, es_password),verify_certs=False,ssl_show_warn=False)  
     

    try:
        team = redisClient.rpop("afl:subreddit")
        if not team:
            return "Queue empty", 200
        job = json.loads(team)
        print("job extracted", flush=True)
        harvestSubreddit(es, job["team"], postLimits=job["limit"])
        print("job done", flush=True)
        return f"Harvested {job['team']}", 200
    except ApiError as e:
        return json.dumps({"error": str(e)}), 500        

    # try:
    #     print("🔄 Running initial team check...", flush=True)
    #     limit = 1000 # fixed inital post per subreddit
    #     for team in TEAM.keys():
    #         print(f"Checking team: {team}", flush=True)
    #         if not initalCheck(es, team):
    #             print(f"Team {team} not harvested yet", flush=True)
    #             continue
    #         else:
    #             print(f"Team {team} already harvested", flush=True)
    #             limit = 10
    #             break 
    #     for i in TEAM.keys():
    #         print(f"📦 Harvesting subreddit for: {i} with limit {limit}", flush=True)  # ✅ Step 5
    #         try:
    #             harvestSubreddit(es,i,postLimits=limit)
    #         except Exception as e:
    #             print(f"Skipping {i} due to error: {e}", flush=True) 
    #             continue 
    #     print("✅ Completed harvesting", flush=True)
    #     return "ok",200
    # except ApiError as e:
    #     return json.dumps({"error": str(e)}), 500
    
    # return "ok", 200
    
    # for i in TEAM.keys():
    #     try:
    #         harvestSubreddit(i,postLimits=1000)
    #     except Exception as e:
    #         print(f"Skipping {i} due to error: {e}")
    #         continue
    
        