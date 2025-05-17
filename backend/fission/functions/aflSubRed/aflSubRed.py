import praw 
from elasticsearch8 import Elasticsearch, exceptions,ApiError  
from datetime import datetime   
import json
from flask import current_app 
import requests  
 


def addElastic(docID,indexText,doc):
    """
    Send data to fission function addelastic to store into elastic
    """
    print("=== addElastic start ===", flush=True)
    url='http://router.fission/addelastic'
    payload = {"indexDocument":indexText,"docID":docID,"doc":doc}  
    try:
        response = requests.post(url, json=payload, timeout=5)
        current_app.logger.info(f'=== aflSubRed: AddElastic : Response: {response.status_code} {response.text} ===') 
    except Exception as e:
        current_app.logger.info(f'=== aflSubRed: AddElastic : Exception in addElastic POST: {str(e)} ===')   
    return "ok"



def main():
    """
    Scrape subreddit suscribers and store into elastic
    
    """
    current_app.logger.info(f'=== aflSubRed: Initialise ===')  
    with open("/secrets/default/elastic-secret/REDDIT_CLIENT_ID") as f:
        clientID = f.read().strip()

    with open("/secrets/default/elastic-secret/REDDIT_CLIENT_SECRET") as f:
        clientSecret = f.read().strip() 
        
    reddit = praw.Reddit(
        client_id=clientID,
        client_secret=clientSecret,
        user_agent="python:reddit-harvester:v1.0 (by /u/Exact_Agency_3144)",
    )
     
    
    with open(f'/configs/default/shared-data/TEAM', 'r') as f:
        teams = list(json.loads(f.read()).keys())  
    try: 
        for team in teams: 
            subs = reddit.subreddit(team).subscribers 
            retrieveDate = datetime.now().isoformat().replace(":", "-")
            docID = f"{team}_{retrieveDate}"
            doc = {
                    "team": team,
                    "subscribers": subs,
                    "retrieveDate": retrieveDate
                }
            addElastic(docID,"afl-fans",doc) 
        return "ok"
    except ApiError as e:
        current_app.logger.info(f'=== aflSubRed: Error occur: {str(e)} ===') 
        return "ok"
        
