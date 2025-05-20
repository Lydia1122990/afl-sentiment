import logging
import json
from typing import Dict, Any, List
from flask import current_app, request
from elasticsearch8 import Elasticsearch

# fission package create --spec --name afl-sentiment-winloss-bluesky-pkg \
# --source ./afl_sentiment_winloss_bluesky/__init__.py \
# --source ./afl_sentiment_winloss_bluesky/afl_sentiment_winloss_bluesky.py \
# --source ./afl_sentiment_winloss_bluesky/requirements.txt \
# --source ./afl_sentiment_winloss_bluesky/build.sh \
# --env python39x --buildcmd './build.sh'

# fission fn create --spec --name afl-sentiment-winloss-bluesky \
# --pkg afl-sentiment-winloss-bluesky-pkg \
# --env python39x \
# --entrypoint "afl_sentiment_winloss_bluesky.main" \
# --specializationtimeout 180 \
# --secret elastic-secret 

# fission route create --spec --name afl-sentiment-winloss-bluesky \
# --function afl-sentiment-winloss-bluesky \
# --method GET \
# --url /afl/sentiment/winloss/bluesky \
# --createingress

# kubectl port-forward service/router -n fission 8080:80

# fission fn log -f --name afl-sentiment-winloss-bluesky
# curl -k http://localhost:8080/afl/sentiment/winloss/bluesky | jq

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

    # Query1
    sentiment_query = {
        "size": 0,
        "query": {"range": {"createdOn": {"gte": "2024-01-01"}}},
        "aggs": {
            "teams": {
                "terms": {"field": "team.keyword", "size": 100},
                "aggs": {
                    "total_sentiment": {"sum": {"field": "sentiment"}},
                    "avg_sentiment": {"avg": {"field": "sentiment"}},
                    "doc_count": {"value_count": {"field": "sentiment"}}
                }
            }
        }
    }

    current_app.logger.info('Executing AFL team sentiment scores query')   
    sentiment_result = es_client.search(index='afl_bluesky_sentiment-18*', body=sentiment_query)
    buckets = sentiment_result.get('aggregations', {}).get('teams', {}).get('buckets', [])

    # Process sentiment data
    teams_sentiment = []
    for team_data in buckets:
        teams_sentiment.append({
            "name": team_data['key'],
            "total_sentiment": team_data['total_sentiment']['value'],
            "avg_sentiment": team_data['avg_sentiment']['value'],
            "doc_count": team_data['doc_count']['value']
        })

    # Query2
    sorted_teams = sorted(teams_sentiment, key=lambda x: x["total_sentiment"], reverse=True)
    top_teams = [TEAM_MAPPING.get(t["name"], t["name"]) for t in sorted_teams[:5]]
    bottom_teams = [TEAM_MAPPING.get(t["name"], t["name"]) for t in sorted_teams[-5:]]

    match_query = {
        "size": 1000,
        "_source": ["team", "result", "year"],
        "query": {
            "bool": {
                "must": [
                    {"terms": {"team.keyword": top_teams + bottom_teams}},
                    {"range": {"year": {"gte": 2024}}}
                ]
            }
        }
    }

    current_app.logger.info('Executing match result query')
    match_result = es_client.search(index="afl-scores*", body=match_query)
    
    # Process match data
    matches = {}
    for hit in match_result["hits"]["hits"]:
        team = hit["_source"]["team"]
        result = hit["_source"].get("result", "")
        if team not in matches:
            matches[team] = {"played": 0, "wins": 0}
        matches[team]["played"] += 1
        if result == "Winner":
            matches[team]["wins"] += 1

    # Calculate win rate
    for team in matches:
        played = matches[team]["played"]
        wins = matches[team]["wins"]
        matches[team]["win_rate"] = round(wins / played, 2) if played > 0 else 0.0

    return {
        "all_teams": teams_sentiment,
        "top_5": top_teams,
        "bottom_5": bottom_teams,
        "matches_data": matches,
        "team_mapping": TEAM_MAPPING
    }