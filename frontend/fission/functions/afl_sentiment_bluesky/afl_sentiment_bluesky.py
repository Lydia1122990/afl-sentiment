import logging
import json
from typing import Dict, Any, List
from flask import current_app, request
from elasticsearch8 import Elasticsearch
  
# fission package create --spec --name afl-sentiment-bluesky-pkg \
# --source ./afl_sentiment_bluesky/__init__.py \
# --source ./afl_sentiment_bluesky/afl_sentiment_reddit.py \
# --source ./afl_sentiment_bluesky/requirements.txt \
# --source ./afl_sentiment_bluesky/build.sh \
# --env python39x --buildcmd './build.sh'

# fission fn create --spec --name afl-sentiment-bluesky \
# --pkg afl-sentiment-bluesky-pkg \
# --env python39x \
# --entrypoint "afl_sentiment_bluesky.main" \
# --specializationtimeout 180 \
# --secret elastic-secret 

# fission route create --spec --name afl-sentiment-bluesky \
# --function afl-sentiment-bluesky \
# --method GET \
# --url /afl/sentiment/bluesky \
# --createingress

def main() -> Dict[str, Any]:
    """Calculate AFL team sentiment scores (average and total) from bluesky from Elasticsearch
    
    Handles:
        - Connect to the Elasticsearch cluster
        - Perform an aggregation query to calculate the total sentiment score and average sentiment scores for each team
        - Find the 5 teams with the highest sentiment scores and the 5 teams with the lowest sentiment scores

    
    Returns:
        JSON response containing:
        - top_5_teams_bluesky: The top 5 teams with the highest sentiments
        - bottom_5_team_bluesky: The top 5 teams with the lowest sentiments
        - all_teams_bluesky: all teams sorted by total sentiment
        - all_teams_count_bluesky: total number of teams

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
            "teams_bluesky": {
                "terms": {
                    "field": "team.keyword",
                    "size": 100  
                },
                "aggs": {
                    "total_sentiment_bluesky": {"sum": {"field": "sentiment"}}, 
                    "avg_sentiment_bluesky": {"avg": {"field": "sentiment"}},
                    "doc_count_bluesky": {"value_count": {"field": "sentiment"}}
                }
            }
        }
    }

    current_app.logger.info('Executing AFL team sentiment scores from bluesky analysis query')
    
    res: Dict[str, Any] = es_client.search(
        index='afl_bluesky_sentiment-18*',  
        body=query_body
    )
    

    # Query result
    teams_data_bluesky: List[Dict[str, Any]] = res.get('aggregations', {}).get('teams_bluesky', {}).get('buckets', [])
        
    if not teams_data_bluesky:
        return {'error': 'cannot find afl-sentiment bluesky data'}, 404
        
        
    all_teams_bluesky = []
    for team_data_bluesky in teams_data_bluesky:
        all_teams_bluesky.append({
            "name": team_data_bluesky['key'],
            "total_sentiment_bluesky": team_data_bluesky['total_sentiment_bluesky']['value'],
            "avg_sentiment_bluesky": team_data_bluesky['avg_sentiment_bluesky']['value'],
            "doc_count_bluesky": team_data_bluesky['doc_count_bluesky']['value']
        }) 

    # Sort by total-sentiment score
    sorted_teams_bluesky = sorted(all_teams_bluesky, key=lambda x: x['total_sentiment_bluesky'], reverse=True)
        

    return {
        'top_5_teams_bluesky': sorted_teams_bluesky[:5],
        'bottom_5_teams_bluesky': sorted_teams_bluesky[-5:][::-1],
        'all_teams_bluesky': sorted_teams_bluesky,
        'all_teams_count_bluesky': len(sorted_teams_bluesky)  
    }