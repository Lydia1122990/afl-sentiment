import logging
import json
from typing import Dict, Any, List
from flask import current_app, request
from elasticsearch8 import Elasticsearch

# fission package create --spec --name afl-subscribers-reddit-pkg \
# --source ./afl_subscribers_reddit/__init__.py \
# --source ./afl_subscribers_reddit/afl_subscribers_reddit.py \
# --source ./afl_subscribers_reddit/requirements.txt \
# --source ./afl_subscribers_reddit/build.sh \
# --env python39x --buildcmd './build.sh'

# fission fn create --spec --name afl-subscribers-reddit \
# --pkg afl-subscribers-reddit-pkg \
# --env python39x \
# --entrypoint "afl_subscribers_reddit.main" \
# --specializationtimeout 180 \
# --secret elastic-secret 

# fission route create --spec --name afl-subscribers-reddit \
# --function afl-subscribers-reddit \
# --method GET \
# --url /afl/subscribers/reddit \
# --createingress

def main() -> Dict[str, Any]:
    """Get AFL team subscriber counts from reddit from Elasticsearch
    
    Handles:
        - Connect to the Elasticsearch cluster
        - Perform a query to get the latest subscriber count for each team
        - Find the 5 teams with the most subscribers and the 5 teams with the least subscribers

    Returns:
        JSON response containing:
        - top_5_teams_subscribers: The top 5 teams with the most subscribers
        - bottom_5_teams_subscribers: The top 5 teams with the least subscribers
        - all_teams_subscribers: all teams sorted by subscriber count
        - all_teams_count: total number of teams

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
    
    # Query to get the latest record for each team
    query_body: Dict[str, Any] = {
        "size": 0,
        "aggs": {
            "teams_group": {
                "terms": {
                    "field": "team.keyword",
                    "size": 100
                },
                "aggs": {
                    "latest_record": {
                        "top_hits": {
                            "size": 1,
                            "sort": [{"retrieveDate.keyword": {"order": "desc"}}],
                            "_source": ["subscribers", "team"]
                        }
                    }
                }
            }
        }
    }

    current_app.logger.info('Executing AFL team subscriber reddit count query')
    
    res: Dict[str, Any] = es_client.search(
        index='afl-fans*',  
        body=query_body
    )
    
    # Query results
    teams_data: List[Dict[str, Any]] = res.get('aggregations', {}).get('teams_group', {}).get('buckets', [])
        
    if not teams_data:
        return {'error': 'cannot find afl-fans reddit data'}, 404
        
    all_teams = []
    for team_data in teams_data:
        latest_record = team_data['latest_record']['hits']['hits'][0]['_source']
        all_teams.append({
            "name": team_data['key'],
            "subscribers": latest_record['subscribers']
        }) 

    # Sort by subscriber count
    sorted_teams = sorted(all_teams, key=lambda x: x['subscribers'], reverse=True)
        
    return {
        'top_5_teams_subscribers': sorted_teams[:5],
        'bottom_5_teams_subscribers': sorted_teams[-5:][::-1],
        'all_teams_subscribers': sorted_teams,
        'all_teams_count': len(sorted_teams)
    }