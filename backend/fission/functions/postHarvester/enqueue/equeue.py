import json
from flask import request, current_app
import redis
from elasticsearch8 import Elasticsearch, exceptions,ApiError 


# fission package create --spec --name enqueue-pkg --source ./functions/enqueue/enqueue.py --source ./functions/enqueue/requirements.txt --env python39 
# fission package create --spec --name enqueue-pkg --source ./functions/enqueue/__init__.py --source ./functions/enqueue/enqueue.py --source ./functions/enqueue/requirements.txt --source ./functions/enqueue/build.sh --env python39 --buildcmd './build.sh'


# fission fn create --spec --name enqueue --pkg enqueue-pkg --env python39 --entrypoint enqueue.main --secret elastic-secret --configmap shared-data 
# fission httptrigger create --spec --name enqueue --url "/enqueue/{topic}" --method POST --function enqueue




def config(key: str) -> list:
    """Reads configuration from shared-data configmap"""
    with open(f'/configs/default/shared-data/{key}', 'r') as f:
        teamData = json.loads(f.read())
        return list(teamData.keys())
    
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

def main():
    """Enqueues Bluesky team jobs into Redis for async processing"""

    # Load Elasticsearch secrets
    with open("/secrets/default/elastic-secret/ES_USERNAME") as f:
        es_username = f.read().strip()
    with open("/secrets/default/elastic-secret/ES_PASSWORD") as f:
        es_password = f.read().strip()

    # Connect to Elasticsearch
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

        for team in config("TEAM"):  # <—— 读取共享的 TEAM 配置
            postCount = getPostCount(es, team.lower())
            limit = 10 if postCount >= 1000 else 1000

            job = {
                "team": team,
                "limit": limit
            }
            current_app.logger.info(
            f'Enqueued to {topic} topic - ' 
            f' job : {job} '
    )

            redisClient.rpush("afl:bluesky", json.dumps(job))
            print(f"Enqueued Bluesky: {team} (limit={limit}, count={postCount})", flush=True)

    return 'ok'
