import logging
import json
from typing import Dict, Any, List
from flask import current_app, request
from elasticsearch8 import Elasticsearch
  
# fission package create --spec --name afl-sentiment-reddit-pkg \
# --source ./afl_sentiment_reddit/__init__.py \
# --source ./afl_sentiment_reddit/afl_sentiment_reddit.py \
# --source ./afl_sentiment_reddit/requirements.txt \
# --source ./afl_sentiment_reddit/build.sh \
# --env python39 --buildcmd './build.sh'

# fission fn create --spec --name afl-sentiment-reddit \
# --pkg afl-sentiment-reddit-pkg \
# --env python39 \
# --entrypoint "afl_sentiment_reddit.main" \
# --specializationtimeout 180 \
# --secret elastic-secret 

# fission route create --spec --name afl-sentiment-reddit \
# --function afl-sentiment-reddit \
# --method GET \
# --url /afl/sentiment/reddit \
# --createingress

def main() -> Dict[str, Any]:
    """Calculate AFL team sentiment scores (average and total) from reddit from Elasticsearch
    
    Handles:
        - Connect to the Elasticsearch cluster
        - Perform an aggregation query to calculate the total sentiment score and average sentiment scores for each team
        - Find the 5 teams with the highest sentiment scores and the 5 teams with the lowest sentiment scores

    
    Returns:
        JSON response containing:
        - top_5_teams_reddit: The top 5 teams with the highest sentiments
        - bottom_5_teams_reddit: The top 5 teams with the lowest sentiments
        - all_teams_reddit: all teams sorted by total sentiment
        - all_teams_count_reddit: total number of teams

    Raises:
        KeyError: If required date parameter is missing
        ElasticsearchException: For query failures
    """

    # Elasticsearch
    with open("/secrets/default/elastic-secret/ES_USERNAME") as f:
        es_username = f.read().strip()

    with open("/secrets/default/elastic-secret/ES_PASSWORD") as f:
        es_password = f.read().strip() 

    es_client: Elasticsearch = Elasticsearch(
        'https://elasticsearch-master.elastic.svc.cluster.local:9200',
        verify_certs=False,  
        ssl_show_warn=False,
        basic_auth=(es_username, es_password) 
    )
    
    # Query
    query_body: Dict[str, Any] = {
        "size": 0,  
        "aggs": {
            "teams_reddit": {
                "terms": {
                    "field": "team.keyword",
                    "size": 100  
                },
                "aggs": {
                    "total_sentiment_reddit": {"sum": {"field": "sentiment"}}, 
                    "avg_sentiment_reddit": {"avg": {"field": "sentiment"}},
                    "doc_count_reddit": {"value_count": {"field": "sentiment"}}
                }
            }
        }
    }

    current_app.logger.info('Executing AFL team sentiment scores from reddit analysis query')
    
    res: Dict[str, Any] = es_client.search(
        index='afl-sentiment*',  
        body=query_body
    )
    

    # Query result
    teams_data_reddit: List[Dict[str, Any]] = res.get('aggregations', {}).get('teams_reddit', {}).get('buckets', [])
        
    if not teams_data_reddit:
        return {'error': 'cannot find afl-sentiment reddit data'}, 404
        
        
    all_teams_reddit = []
    for team_data_reddit in teams_data_reddit:
        all_teams_reddit.append({
            "name": team_data_reddit['key'],
            "total_sentiment_reddit": team_data_reddit['total_sentiment_reddit']['value'],
            "avg_sentiment_reddit": team_data_reddit['avg_sentiment_reddit']['value'],
            "doc_count_reddit": team_data_reddit['doc_count_reddit']['value']
        }) 

    # Sort by total-sentiment score
    sorted_teams_reddit = sorted(all_teams_reddit, key=lambda x: x['total_sentiment_reddit'], reverse=True)
        

    return {
        'top_5_teams_reddit': sorted_teams_reddit [:5],
        'bottom_5_teams_reddit': sorted_teams_reddit [-5:][::-1],
        'all_teams_reddit': sorted_teams_reddit ,
        'all_teams_count_reddit': len(sorted_teams_reddit )  
    }