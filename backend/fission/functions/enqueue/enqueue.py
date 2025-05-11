# import logging
import json
from typing import Dict, Any, Optional
from flask import current_app, request
import redis
from elasticsearch8 import Elasticsearch, exceptions,ApiError 


# fission package create --spec --name enqueue-pkg --source ./functions/enqueue/enqueue.py --source ./functions/enqueue/requirements.txt --env python39 
# fission package create --spec --name enqueue-pkg --source ./functions/enqueue/__init__.py --source ./functions/enqueue/enqueue.py --source ./functions/enqueue/requirements.txt --source ./functions/enqueue/build.sh --env python39 --buildcmd './build.sh'


# fission fn create --spec --name enqueue --pkg enqueue-pkg --env python39 --entrypoint enqueue.main --secret elastic-secret --configmap shared-data
# fission route create --spec --name enqueue-route --function enqueue --url /enqueue --method POST --createingress




def config(key: str) -> list:
    """Reads configuration from share data file J2QQAE1UEqi5JVZ"""
    
    with open(f'/configs/default/shared-data/{key}', 'r') as f:
        teamData = json.loads(f.read())
        return json.dumps({"status": "ok", "teams": list(teamData.keys())}) 
    
def getPostCount(es, team):
    """
    Returns total documents in ES for a given team
    """
    query = {
        "query": {
            "term": {
                "team.keyword": team
            }
        }
    }
    result = es.count(index="afl-sentiment", body=query)
    return result.get("count", 0)

def main():
    
    with open("/secrets/default/elastic-secret/ES_USERNAME") as f:
        es_username = f.read().strip()

    with open("/secrets/default/elastic-secret/ES_PASSWORD") as f:
        es_password = f.read().strip()  
        
    es = Elasticsearch(
    hosts=["https://elasticsearch-master.elastic.svc.cluster.local:9200"],
    basic_auth=(es_username, es_password),verify_certs=False,ssl_show_warn=False) 
    
    req: Request = request
    topic: Optional[str] = req.headers.get('X-Fission-Params-Topic')
    
    redisClient: redis.StrictRedis = redis.StrictRedis(
        host='redis-headless.redis.svc.cluster.local',
        socket_connect_timeout=5,
        decode_responses=False
    )
    
    
    # Structured logging with message metrics
    current_app.logger.info(
        f'Enqueued to {topic} topic - ' 
    )
    
    if str(topic) == "TEAM":
        for team in config("TEAM"):
            postCount = getPostCount(es, team.lower())
            limit = 100 if postCount >= 1000 else 1000

            job = {
                "team": team,
                "limit": limit
            }

            redisClient.rpush("afl:subreddit", json.dumps(job))
            print(f"🔁 Enqueued {team} with limit {limit} (count = {postCount})")

    return 'OK' 