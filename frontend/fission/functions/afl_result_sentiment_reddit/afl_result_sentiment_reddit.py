import logging
from typing import Dict, Any, List
from flask import current_app, request
from elasticsearch8 import Elasticsearch

# fission package create --spec --name afl-result-sentiment-reddit-pkg \
# --source ./afl_result_sentiment_reddit/__init__.py \
# --source ./afl_result_sentiment_reddit/afl_result_sentiment_reddit.py \
# --source ./afl_result_sentiment_reddit/requirements.txt \
# --source ./afl_result_sentiment_reddit/build.sh \
# --env python39x --buildcmd './build.sh'

# fission fn create --spec --name afl-result-sentiment-reddit \
# --pkg afl-result-sentiment-reddit-pkg \
# --env python39x \
# --entrypoint "afl_result_sentiment_reddit.main" \
# --specializationtimeout 180 \
# --secret elastic-secret 

# fission route create --spec --name afl-result-sentiment-reddit \
# --function afl-result-sentiment-reddit \
# --method GET \
# --url /afl/result/sentiment/reddit \
# --createingress

# Team mapping: "afl-sentiment": "afl-scores"
TEAM_MAPPING = {
    "richmondfC": "Richmond",
    "adelaidefc": "Adelaide",
    "carltonblues": "Carlton",
    "stkilda": "St Kilda",
    "essendonfc": "Essendon",
    "geelongcats": "Geelong",
    "hawktalk": "Hawthorn",
    "melbournefc": "Melbourne",
    "northmelbournefc": "North Melbourne",
    "westcoasteagles": "West Coast",
    "collingwoodfc": "Collingwood",
    "gcfc": "Gold Coast",
    "sydneyswans": "Sydney",
    "westernbulldogs": "Western Bulldogs",
    "fremantlefc": "Fremantle",
    "gwsgiants": "Greater Western Sydney", 
    "weareportadelaide": "Port Adelaide",
    "brisbanelions": "Brisbane Lions",
}

def main() -> Dict[str, Any]:
    
    """Calculate AFL team sentiment scores (average and total) grouped by week
        and Retrieve match records for these teams from reddit from Elasticsearch
    
    Handles:
        - Connect to the Elasticsearch cluster
        - Perform an aggregation query to calculate the total sentiment score and average sentiment scores for each team
        - Generate time-series sentiment data grouped by week (configurable via X-Date-Format header)
        - Identify top 5 and bottom 5 teams by sentiment score
        - Retrieve match records for these teams from afl-scores* index (after 2024)
        

    Returns:
        JSON response containing:
        - sentiment_data:
            "all_teams": Complete list of teams with sentiment metrics
            "top_5": The top 5 teams with the highest sentiments
            "bottom_5": The top 5 teams with the lowest sentiments
            "date_format": Time grouping interval (week)
        - match_data: match result data top/bottom teams (after 2024)
        - team_mapping: team name mapping

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

    # Query1: Get sentiment data with time series (week)
    # Group by team and calculate the total sentiment score, average score and number of documents for each team
    # Generate time series data by time granularity (week) and calculate the average and total sentiment score for each period
    date_format = request.headers.get('X-Date-Format', 'week') # Get the time granularity from the request header
    
    sentiment_query = {
        "size": 0,
        "query": {"range": {"createdOn": {"gte": "2024-01-01"}}},
        "aggs": {
            "teams": {
                "terms": {"field": "team.keyword", "size": 100}, # Group by team
                "aggs": {
                    "total_sentiment": {"sum": {"field": "sentiment"}},
                    "avg_sentiment": {"avg": {"field": "sentiment"}},
                    "doc_count": {"value_count": {"field": "sentiment"}},
                    "sentiment_over_time": {
                        "date_histogram": {
                            "field": "createdOn",
                            "calendar_interval": date_format, # Group by week
                            "format": "yyyy-MM-dd"
                        },
                        "aggs": {
                            "period_avg": {"avg": {"field": "sentiment"}}, # Average score for each period
                            "period_total": {"sum": {"field": "sentiment"}} # Total score for each period
                        }
                    }
                }
            }
        }
    }

    current_app.logger.info('Executing AFL team sentiment scores from reddit analysis query')

    sentiment_result: Dict[str, Any] = es_client.search(index='afl-sentiment', body=sentiment_query)
    buckets: List[Dict[str, Any]] = sentiment_result.get('aggregations', {}).get('teams', {}).get('buckets', [])

    # Process sentiment data
    teams_sentiment = []
    for team_data in buckets:
        time_series = [
            {
                "date": bucket['key_as_string'],
                "avg_sentiment": bucket['period_avg']['value'],
                "total_sentiment": bucket['period_total']['value'],
                "doc_count": bucket['doc_count']
            }
            for bucket in team_data['sentiment_over_time']['buckets']
            if bucket['doc_count'] > 0 # Filter time periods with no data
        ]
        
        teams_sentiment.append({
            "name": team_data['key'],
            "total_sentiment": team_data['total_sentiment']['value'],
            "avg_sentiment": team_data['avg_sentiment']['value'],
            "doc_count": team_data['doc_count']['value'],
            "time_series": time_series
        })

    # Query2: Get the match result data
    sorted_teams = sorted(teams_sentiment, key=lambda x: x["total_sentiment"], reverse=True)
    top_teams = [TEAM_MAPPING.get(t["name"], t["name"]) for t in sorted_teams[:5]]
    bottom_teams = [TEAM_MAPPING.get(t["name"], t["name"]) for t in sorted_teams[-5:]]
    
    match_query = {
        "size": 1000,
        "_source": ["team", "result", "date", "opponent", "score", "opponentScore", "venue"],
        "query": {
            "bool": {
                "must": [
                    {"terms": {"team.keyword": top_teams + bottom_teams}},
                    {"range": {"date": {"gte": "2024-01-01"}}}
                ]
            }
        }
    }

    current_app.logger.info('Executing match result from reddit analysis query')

    match_result = es_client.search(index="afl-scores*", body=match_query)
    matches = [hit["_source"] for hit in match_result["hits"]["hits"]] # Extract match records

    return {
        "sentiment_data": {
            "all_teams": teams_sentiment,
            "top_5": sorted_teams[:5],
            "bottom_5": sorted_teams[-5:],
            "date_format": date_format
        },
        "match_data": matches,
        "team_mapping": TEAM_MAPPING
    }