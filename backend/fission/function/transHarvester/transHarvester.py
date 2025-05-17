import json
import time
import praw
import redis
import requests
import nltk
from datetime import datetime
nltk.download('punkt_tab')
from praw.reddit import Subreddit
from nltk.tokenize import sent_tokenize
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from elasticsearch8 import ApiError
from elasticsearch8 import exceptions
from elasticsearch8 import Elasticsearch

sentimentAnalyser = SentimentIntensityAnalyzer()
# List of city names (to be provided by user)
CITY = {
"Melbourne": [
  "melbourne train",
  "melbourne tram",
  "melbourne bus",
  "melbourne metro",
  "melbourne shuttle",
  "melbourne light rail",
  "melbourne skybus",
  "melbourne myki",
  "melbourne vline",
  "melbourne yarratrams",
  "melbourne metro trains",
  "melbourne train delay",
  "melbourne tram delay",
  "melbourne bus delay",
  "melbourne train fare",
  "melbourne tram fare",
  "melbourne bus fare",
  "melbourne train ticket",
  "melbourne tram ticket",
  "melbourne bus ticket",
  "melbourne overcrowded train",
  "melbourne overcrowded tram",
  "melbourne overcrowded bus",
  "melbourne track maintenance",
  "melbourne bus replacement"
],

"Sydney": [
  "sydney train",
  "sydney tram",
  "sydney bus",
  "sydney metro",
  "sydney light rail",
  "sydney ferry",
    "opal",
  "sydney train delay",
  "sydney tram delay",
  "sydney bus delay",
  "sydney train fare",
  "sydney tram fare",
  "sydney bus fare",
  "sydney train ticket",
  "sydney tram ticket",
  "sydney bus ticket",
  "sydney overcrowded train",
  "sydney overcrowded tram",
  "sydney overcrowded bus",
  "sydney track maintenance",
  "sydney bus replacement"
],

"Brisbane": [
  "brisbane train",
  "brisbane tram",
  "brisbane bus",
  "brisbane metro",
  "brisbane shuttle",
  "brisbane light rail",
  "brisbane translink",
  "brisbane gocard",
  "brisbane train delay",
  "brisbane tram delay",
  "brisbane bus delay",
  "brisbane train fare",
  "brisbane tram fare",
  "brisbane bus fare",
  "brisbane train ticket",
  "brisbane tram ticket",
  "brisbane bus ticket",
  "brisbane overcrowded train",
  "brisbane overcrowded tram",
  "brisbane overcrowded bus",
  "brisbane track maintenance",
  "brisbane bus replacement"
],

"Adelaide": [
  "adelaide train",
  "adelaide tram",
  "adelaide bus",
  "adelaide metro",
  "adelaide shuttle",
  "adelaide light rail",
  "adelaide adelaidemetro",
  "adelaide metrocard",
  "adelaide train delay",
  "adelaide tram delay",
  "adelaide bus delay",
  "adelaide train fare",
  "adelaide tram fare",
  "adelaide bus fare",
  "adelaide train ticket",
  "adelaide tram ticket",
  "adelaide bus ticket",
  "adelaide overcrowded train",
  "adelaide overcrowded tram",
  "adelaide overcrowded bus",
  "adelaide track maintenance",
  "adelaide bus replacement"
],

"Perth": [
  "perth train",
  "perth tram",
  "perth bus",
  "perth metro",
  "perth shuttle",
  "perth light rail",
  "perth transperth",
  "perth train delay",
  "perth tram delay",
  "perth bus delay",
  "perth train fare",
  "perth tram fare",
  "perth bus fare",
  "perth train ticket",
  "perth tram ticket",
  "perth bus ticket",
  "perth overcrowded train",
  "perth overcrowded tram",
  "perth overcrowded bus",
  "perth track maintenance",
  "perth bus replacement"
],

"Canberra": [
  "canberra train",
  "canberra tram",
  "canberra bus",
  "canberra metro",
  "canberra shuttle",
  "canberra light rail",
  "canberra act transport",
  "canberra myway",
  "canberra train delay",
  "canberra tram delay",
  "canberra bus delay",
  "canberra train fare",
  "canberra tram fare",
  "canberra bus fare",
  "canberra train ticket",
  "canberra tram ticket",
  "canberra bus ticket",
  "canberra overcrowded train",
  "canberra overcrowded tram",
  "canberra overcrowded bus",
  "canberra track maintenance",
  "canberra bus replacement"
],

"Hobart": [
  "hobart train",
  "hobart tram",
  "hobart bus",
  "hobart metro",
  "hobart shuttle",
  "hobart light rail",
  "hobart bus service",
  "hobart train delay",
  "hobart tram delay",
  "hobart bus delay",
  "hobart train fare",
  "hobart tram fare",
  "hobart bus fare",
  "hobart train ticket",
  "hobart tram ticket",
  "hobart bus ticket",
  "hobart overcrowded train",
  "hobart overcrowded tram",
  "hobart overcrowded bus",
  "hobart track maintenance",
  "hobart bus replacement"
],

"Darwin": [
  "darwin train",
  "darwin tram",
  "darwin bus",
  "darwin metro",
  "darwin shuttle",
  "darwin light rail",
  "darwinbus",
  "darwin train delay",
  "darwin tram delay",
  "darwin bus delay",
  "darwin train fare",
  "darwin tram fare",
  "darwin bus fare",
  "darwin train ticket",
  "darwin tram ticket",
  "darwin bus ticket",
  "darwin overcrowded train",
  "darwin overcrowded tram",
  "darwin overcrowded bus",
  "darwin track maintenance",
  "darwin bus replacement"
]
}
cityNickname = {}
for city, nicknames in CITY.items():
    for alias in nicknames:
        cityNickname[alias.lower()] = city

def cityContain(text, cities = cityNickname):
    """
    Check if any city name is in the text.
    """
    foundCity = set()
    for nickname, city in cities.items():
        if nickname in text.lower():
            foundCity.add(city)
    return list(foundCity)

def cleanText(text):
    """
    Send text to fission fucntion text-clean for cleaning and return cleaned text
    """
    url='http://router.fission/text-clean'
    payload = {"text":text}
    response = requests.post(url,json=payload)
    return response.json()["cleanedText"]

def sentimentPerCity(text,postSub, upvoteScore=1, cities=CITY):
    """
    Get total weighted sentiment per city , if city is not mentioned in posts then assumed its related to subredit city
    """
    sentences = sent_tokenize(text)
    citySentiment = {city: [] for city in cities}
    
    for sentence in sentences:
        sentiment = sentimentAnalyser.polarity_scores(sentence)['compound'] 
        for city, nicknames in CITY.items():
            cityFound = any(nickname in sentence.lower() for nickname in nicknames)
            if cityFound:
                citySentiment[city].append(sentiment * abs(upvoteScore)) # multiple by upvote score to get weighted sentiment
        if not cityFound:
            if postSub not in citySentiment:
                citySentiment[postSub] = []
            sentiment = sentimentAnalyser.polarity_scores(sentence)['compound']
            citySentiment[postSub].append(sentiment * abs(upvoteScore))
    resultSentiment = {}
    for city,sentiments in citySentiment.items(): 
        if sentiments and upvoteScore != 0:
            # weighted avg sentment where theres more than one sentiment v alue total sentiment / upvote*number of sentence
            resultSentiment[city] = round(sum(sentiments) / (abs(upvoteScore) * len(sentiments)), 3)
        else:
            resultSentiment[city] = 0.0
        
    return resultSentiment 

def storeElastic(es,text,post,postType,sentiments, citiesBool,commentID=False)  -> str:
    """
    store data into elastic, docid base on its comment ID and post ID, if post does not mention city then consdier subreddit city 
    """
    try:
        count = 0 
        if citiesBool:
            print("storeElastic start, flush=True")
            for city,sentiment in sentiments.items(): 
                docId = (f"{commentID}_{city}_comment " if commentID else  f"{post.id}_{city}_{postType}").lower() 
                doc = {"type": postType,
                       "platform":"Reddit",                       
                      "city": city.lower(),
                      "sentiment":sentiment,
                      "text": text,
                      "upvote":post.score,
                      "createdOn": datetime.fromtimestamp(post.created_utc).isoformat(),
                      "url":post.url,
                }
                es.create(index="trans-reddit-sentiment", id=docId, document=doc)
                print(f"added {docId} {post.subreddit.display_name.lower()}", flush=True)
                # print(json.dumps(doc,indent=4,sort_keys=True))
        else:
            count += 1
            print("storeElastic start, flush=True")
            docId = (f"{commentID}_{post.subreddit.display_name.lower()}_comment " if commentID else  f"{post.id}_{post.subreddit.display_name.lower()}_{postType}").lower() 
            doc = {"type": postType,
                   "platform":"Reddit",  
                      "city": post.subreddit.display_name.lower(),
                      "sentiment":sentiments,
                      "text": text,
                      "upvote":post.score,
                      "createdOn": datetime.fromtimestamp(post.created_utc).isoformat(),
                      "url":post.url,
                }  
            es.create(index="trans-reddit-sentiment", id=docId, document=doc)
            print(f"added {count} {docId} {post.subreddit.display_name.lower()}", flush=True)
            # print(json.dumps(doc,indent=4,sort_keys=True))
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
        "type": "harvest-flag",
        "platform": "Reddit",
        "city": subredditName.lower(),
        "last": postFullname.lower(),
        "updatedOn": datetime.now().isoformat()
    }
    print(f"store {docId}")
    es.index(index="trans-harvest-details", id=docId, document=doc)
    return "ok"

def fetchLastPost(es, subredditName):
    """
    Fetch last post details
    """
    docId = f"last-{subredditName.lower()}"
    print(f"fetch {docId}")
    try:
        doc = es.get(index="trans-harvest-details", id=docId)
        return doc["_source"].get("last", None)
    except exceptions.NotFoundError:
        return None       
 
def harvestSubreddit(es,redditCity, postLimits=10) -> str:
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
    subreddit = reddit.subreddit(redditCity) 
    after = fetchLastPost(es, redditCity) 
    
    lastPost = None
    for post in subreddit.new(limit=postLimits): 
        print(post.url)
        if after == post.fullname.lower():
            #reach last scrapped post then break
            break
        text = cleanText(post.title + " " + post.selftext)
        print(text)
        postCities = cityContain(text)

        if postCities:
            sentiment = sentimentPerCity(text,post.subreddit.display_name.lower(),post.score, postCities) 
            storeElastic(es,text,post,"post",sentiment,True)
        else: 
            sentiment =  sentimentAnalyser.polarity_scores(text)['compound']  
            storeElastic(es,text,post,"post",sentiment,False)
            
        post.comments.replace_more(limit=0) 
        
        for comment in post.comments.list():
            commentText = cleanText(comment.body)
            commentCities = cityContain(commentText)
            # Skip if it's reply to another comment AND doesn't mention a city
            if comment.parent_id.startswith("t1_") and not commentCities:
                continue 
            if commentCities: 
                sentiment = sentimentPerCity(commentText,post.subreddit.display_name.lower(), comment.score, commentCities)
                storeElastic(es,commentText,post,"comment",sentiment,True,comment.id)
        
        lastPost = post.fullname
    if lastPost:
        #Store last post details
        saveLastPost(es,redditCity,lastPost)
    return "ok"
        
        


def main():
    """
    Run harvest subreddit for all Cities, skip if we get an conflicterror
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
        city = redisClient.rpop("trans:subreddit")
        if not city:
            return "Queue empty", 200
        job = json.loads(city)
        harvestSubreddit(es, job["city"], postLimits=job["limit"])
        print("job done", flush=True)
        return f"Harvested {job['city']}", 200
    except ApiError as e:
        return json.dumps({"error": str(e)}), 500       

   
