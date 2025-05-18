# import logging
import json
from typing import Dict, Any, Optional
from flask import current_app, request
import redis
from elasticsearch8 import Elasticsearch, exceptions,ApiError 


# fission package create --spec --name enqueue-pkg --source ./functions/enqueue/enqueue.py --source ./functions/enqueue/requirements.txt --env python39 
# fission package create --spec --name enqueue-pkg --source ./functions/enqueue/__init__.py --source ./functions/enqueue/enqueue.py --source ./functions/enqueue/requirements.txt --source ./functions/enqueue/build.sh --env python39 --buildcmd './build.sh'


# fission fn create --spec --name enqueue --pkg enqueue-pkg --env python39 --entrypoint enqueue.main --secret elastic-secret --configmap shared-data 
# fission httptrigger create --spec --name enqueue --url "/enqueue/{topic}" --method POST --function enqueue





def config(key: str) -> list:
    """Reads configuration from share data file """
    
    with open(f'/configs/default/shared-data/{key}', 'r') as f:
        Data = json.loads(f.read())
        return list(Data.keys())
    
def getPostCount(es, team):
    """
    Returns total documents in ES for a given team
    """
    query = {
        "query": {
            "bool": {
                "must": [
                    { "term": { "team.keyword": team }},
                    { "term": { "type.keyword": "post" }}
                ]
            }
        }
    }
    result = es.count(index="afl-sentiment", body=query)
    return result.get("count", 0)

def getTransPostCount(es, city):
    """
    Returns total documents in ES for a given city
    """
    query = {
        "query": {
            "bool": {
                "must": [
                    { "term": { "city.keyword": city }},
                    { "term": { "type.keyword": "post" }}
                ]
            }
        }
    }
    result = es.count(index="trans-reddit-sentiment", body=query)
    return result.get("count", 0)


def main() -> str:
    """Message queue producer for Redis streaming.

    Handles:
    - Redis connection pooling
    - JSON payload serialization
    - Topic-based message routing via headers
    - Message size logging

    Returns:
        'OK' with HTTP 200 on successful enqueue

    Raises:
        redis.RedisError: For connection/operation failures
        JSONDecodeError: If invalid payload received
    """

    with open("/secrets/default/elastic-secret/ES_USERNAME") as f:
        es_username = f.read().strip()

    with open("/secrets/default/elastic-secret/ES_PASSWORD") as f:
        es_password = f.read().strip()  
        
    es = Elasticsearch(
    hosts=["https://elasticsearch-master.elastic.svc.cluster.local:9200"],
    basic_auth=(es_username, es_password),verify_certs=False,ssl_show_warn=False) 
    
    req: Request = request
    topic: Optional[str] = req.headers.get('X-Fission-Params-Topic',"TEAM")
    
    redisClient: redis.StrictRedis = redis.StrictRedis(
        host='redis-headless.redis.svc.cluster.local',
        socket_connect_timeout=5,
        decode_responses=False
    )
    
    
    # Structured logging with message metrics
    
    
    if str(topic).upper() == "TEAM":
        
        if redisClient.llen("afl:subreddit") > 50:
            # skipped enqueue to avoid over scaling
            print("Too many unprocessed jobs — skipping enqueue this round.")
            return "ok"
        for team in config("TEAM"):
            postCount = getPostCount(es, team.lower())
            limit = 10 if postCount >= 500 else 500

            job = {
                "team": team,
                "limit": limit
            }
            current_app.logger.info(
            f'Enqueued to {topic} topic - ' 
            f' job : {job} '
    )

            redisClient.rpush("afl:subreddit", json.dumps(job))
            print(f"Enqueued {team} with limit {limit} (count = {postCount})",flush=True)
    elif str(topic).upper() == "CITY":
        
        if redisClient.llen("trans:subreddit") > 50:
            # skipped enqueue to avoid over scaling
            print("Too many unprocessed jobs — skipping enqueue this round.")
            return "ok"
        for city in config("CITY"):
            postCount = getTransPostCount(es, city.lower())
            limit = 10 if postCount >= 1000 else 1000

            job = {
                "city": city,
                "limit": limit
            }
            current_app.logger.info(
                f'Enqueued to {topic} topic - ' 
                f' job : {job} '
            )

            redisClient.rpush("trans:subreddit", json.dumps(job))
            print(f"Enqueued {city} with limit {limit} (count = {postCount})",flush=True)

    return 'ok' 