import logging
from typing import Dict, Any, List
from flask import current_app
from elasticsearch8 import Elasticsearch

# fission package create --spec --name afl-post-comparison-pkg \
# --source ./afl_post_comparison/__init__.py \
# --source ./afl_post_comparison/afl_post_comparison.py \
# --source ./afl_post_comparison/requirements.txt \
# --source ./afl_post_comparison/build.sh \
# --env python39x --buildcmd './build.sh'

# fission fn create --spec --name afl-post-comparison \
# --pkg afl-post-comparison-pkg \
# --env python39x \
# --entrypoint "afl_post_comparison.main" \
# --specializationtimeout 180 \
# --secret elastic-secret 
# 
# fission route create --spec --name afl-post-comparison \
# --function afl-post-comparison \
# --method GET \
# --url /afl/post/comparison \
# --createingress

# kubectl port-forward service/router -n fission 8080:80

# fission fn log -f --name afl-post-comparison
# curl -k http://localhost:8080/afl/post/comparison | jq

def main() -> Dict[str, Any]:
    """Compare AFL team sentiment between Reddit and Bluesky
    
    Returns:
        JSON response containing:
        - total_posts: Total posts count for each platform
        - team_comparison: List of teams with post counts and sentiment for both platforms
    """
    
    # Elasticsearch connection
    with open("/secrets/default/elastic-secret/ES_USERNAME") as f:
        es_username = f.read().strip()
    with open("/secrets/default/elastic-secret/ES_PASSWORD") as f:
        es_password = f.read().strip()

    es_client = Elasticsearch(
        'https://elasticsearch-master.elastic.svc.cluster.local:9200',
        verify_certs=False,
        ssl_show_warn=False,
        basic_auth=(es_username, es_password)
    )
    
    # Reddit query
    reddit_query = {
        "size": 0,
        "aggs": {
            "teams": {
                "terms": {"field": "team.keyword", "size": 100},
                "aggs": {
                    "total_sentiment": {"sum": {"field": "sentiment"}},
                    "avg_sentiment": {"avg": {"field": "sentiment"}},
                    "doc_count": {"value_count": {"field": "sentiment"}}
                }
            },
            "total_posts": {"value_count": {"field": "sentiment"}}
        }
    }

    # Bluesky query
    bluesky_query = {
        "size": 0,
        "aggs": {
            "teams": {
                "terms": {"field": "team.keyword", "size": 100},
                "aggs": {
                    "total_sentiment": {"sum": {"field": "sentiment"}},
                    "avg_sentiment": {"avg": {"field": "sentiment"}},
                    "doc_count": {"value_count": {"field": "sentiment"}}
                }
            },
            "total_posts": {"value_count": {"field": "sentiment"}}
        }
    }
    
    # Execute queries
    current_app.logger.info('Executing Reddit and Bluesky queries')
    reddit_res = es_client.search(index='afl-sentiment', body=reddit_query)
    bluesky_res = es_client.search(index='afl_bluesky_sentiment-18', body=bluesky_query)
    
    # Process data
    reddit_teams = process_team_data(reddit_res, 'reddit')
    reddit_total = reddit_res['aggregations']['total_posts']['value']
    
    bluesky_teams = process_team_data(bluesky_res, 'bluesky')
    bluesky_total = bluesky_res['aggregations']['total_posts']['value']
    
    # Merge data
    team_comparison = merge_team_data(reddit_teams, bluesky_teams)

    return {
        'total_posts': {
            'reddit': reddit_total,
            'bluesky': bluesky_total
        },
        'team_comparison': team_comparison
    }

# Process team data from Elasticsearch response
def process_team_data(res: Dict[str, Any], platform: str) -> List[Dict[str, Any]]:
    teams_data = res.get('aggregations', {}).get('teams', {}).get('buckets', [])
    return [{
        "name": team['key'],
        "total_sentiment": team['total_sentiment']['value'],
        "avg_sentiment": team['avg_sentiment']['value'],
        "doc_count": team['doc_count']['value']
    } for team in teams_data]

# Merge data from both platforms for each team
def merge_team_data(reddit_data: List[Dict[str, Any]], bluesky_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    all_teams = set(team['name'] for team in reddit_data) | set(team['name'] for team in bluesky_data)
    
    merged = []
    for team in all_teams:
        reddit = next((t for t in reddit_data if t['name'] == team), None)
        bluesky = next((t for t in bluesky_data if t['name'] == team), None)
        
        merged.append({
            'name': team,
            'reddit_posts': reddit['doc_count'] if reddit else 0,
            'reddit_avg_sentiment': reddit['avg_sentiment'] if reddit else 0,
            'reddit_total_sentiment': reddit['total_sentiment'] if reddit else 0,
            'bluesky_posts': bluesky['doc_count'] if bluesky else 0,
            'bluesky_avg_sentiment': bluesky['avg_sentiment'] if bluesky else 0,
            'bluesky_total_sentiment': bluesky['total_sentiment'] if bluesky else 0
        })
    
    return sorted(merged, key=lambda x: x['reddit_posts'] + x['bluesky_posts'], reverse=True)