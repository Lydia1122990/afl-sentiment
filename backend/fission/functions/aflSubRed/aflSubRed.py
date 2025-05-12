import praw 
from elasticsearch8 import Elasticsearch, exceptions,ApiError  
from datetime import datetime   
import json

# fission package create --spec --name aflsubred-pkg --source ./functions/aflSubRed/aflSubRed.py --source ./functions/aflSubRed/requirements.txt --env python39 
# fission fn create --spec --name aflsubred --pkg aflsubred-pkg --env python39 --entrypoint aflSubRed.main --secret elastic-secret --configmap shared-data 
# fission route create --spec --name aflsubred-route --function aflsubred --url /aflsubred --method POST --createingress
# run every 12 hours
# fission timer create \
#   --spec \
#   --name aflsubred-timer \
#   --function aflsubred \
#   --cron "0 */12 * * *"
  

def main():
    with open("/secrets/default/elastic-secret/REDDIT_CLIENT_ID") as f:
        clientID = f.read().strip()

    with open("/secrets/default/elastic-secret/REDDIT_CLIENT_SECRET") as f:
        clientSecret = f.read().strip() 
        
    reddit = praw.Reddit(
        client_id=clientID,
        client_secret=clientSecret,
        user_agent="python:reddit-harvester:v1.0 (by /u/Exact_Agency_3144)",
    )
    
    with open("/secrets/default/elastic-secret/ES_USERNAME") as f:
        es_username = f.read().strip()

    with open("/secrets/default/elastic-secret/ES_PASSWORD") as f:
        es_password = f.read().strip() 
        
    es = Elasticsearch(
    hosts=["https://elasticsearch-master.elastic.svc.cluster.local:9200"],
    basic_auth=(es_username, es_password),verify_certs=False,ssl_show_warn=False) 
    
    
    with open(f'/configs/default/shared-data/TEAM', 'r') as f:
        teams = list(json.loads(f.read()).keys())  
    try:
        print(teams,flush=True)
        for team in teams: 
            subs = reddit.subreddit(team).subscribers 
            retrieveDate = datetime.now().isoformat().replace(":", "-")
            docID = f"{team}_{retrieveDate}"
            doc = {
                    "team": team,
                    "subscribers": subs,
                    "retrieveDate": retrieveDate
                }
            es.create(index="afl-fans", id=docID, document=doc)
        return "ok"
    except exceptions.ConflictError:
        print(f"Document already exists, skipping...")
        return "ok"
        
