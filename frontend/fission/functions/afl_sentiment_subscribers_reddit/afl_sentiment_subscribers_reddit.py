import logging
from typing import Dict, Any, List
from flask import current_app, request
from elasticsearch8 import Elasticsearch

# fission package create --spec --name afl-sentiment-subscribers-reddit-pkg \
# --source ./afl_sentiment_subscribers_reddit/__init__.py \
# --source ./afl_sentiment_subscribers_reddit/afl_sentiment_subscribers_reddit.py \
# --source ./afl_sentiment_subscribers_reddit/requirements.txt \
# --source ./afl_sentiment_subscribers_reddit/build.sh \
# --env python39x --buildcmd './build.sh'

# fission fn create --spec --name afl-sentiment-subscribers-reddit \
# --pkg afl-sentiment-subscribers-reddit-pkg \
# --env python39x \
# --entrypoint "afl_sentiment_subscribers_reddit.main" \
# --specializationtimeout 180 \
# --secret elastic-secret 

# fission route create --spec --name afl-sentiment-subscribers-reddit \
# --function afl-sentiment-subscribers-reddit \
# --method GET \
# --url /afl/sentiment/subscribers/reddit \
# --createingress

# kubectl port-forward service/elasticsearch-master -n elastic 9200:9200
# kubectl port-forward service/kibana-kibana -n elastic 5601:5601
# kubectl port-forward service/router -n fission 8080:80

# fission fn log -f --name afl-sentiment-subscribers-reddit
# curl -k http://localhost:8080/afl/sentiment/subscribers/reddit | jq

# Team mapping: "afl-sentiment": "afl-fans"
TEAM_MAPPING = {
    "richmondfC": "RichmondFC",
    "adelaidefc": "adelaidefc",
    "carltonblues": "CarltonBlues",
    "stkilda": "StKilda",
    "essendonfc": "EssendonFC",
    "geelongcats": "GeelongCats",
    "hawktalk": "hawktalk",
    "melbournefc": "melbournefc",
    "northmelbournefc": "NorthMelbourneFC",
    "westcoasteagles": "westcoasteagles",
    "collingwoodfc": "collingwoodfc",
    "gcfc": "gcfc",
    "sydneyswans": "sydneyswans",
    "westernbulldogs": "westernbulldogs",
    "fremantlefc": "FremantleFC",
    "gwsgiants": "GWSgiants",
    "weareportadelaide": "weareportadelaide",
    "brisbanelions": "brisbanelions",
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

    # Query1: Get sentiment data with time series (day)
    # Group by team and calculate the total sentiment score, average score and number of documents for each team
    # Generate time series data by time granularity (day) and calculate the average and total sentiment score for each period
    # date_format = request.headers.get('X-Date-Format', 'week')
    sentiment_query = {
        "size": 0,
        "query": {"range": {"createdOn": {"gte": "2025-05-01"}}},
        "aggs": {
            "teams": {
                "terms": {"field": "team.keyword", "size": 100},
                "aggs": {
                    "total_sentiment": {"sum": {"field": "sentiment"}},
                    "avg_sentiment": {"avg": {"field": "sentiment"}},
                    "doc_count": {"value_count": {"field": "sentiment"}},
                    "sentiment_over_time": {
                        "date_histogram": {
                            "field": "createdOn",
                            "calendar_interval": "1d", # Aggregation by day
                            "format": "yyyy-MM-dd"
                        },
                        "aggs": {
                            "period_avg": {"avg": {"field": "sentiment"}},
                            "period_total": {"sum": {"field": "sentiment"}}
                        }
                    }
                }
            }
        }
    }

    current_app.logger.info('Executing AFL team sentiment scores from reddit analysis query')

    sentiment_result = es_client.search(index='afl-sentiment*', body=sentiment_query)
    sentiment_buckets = sentiment_result.get('aggregations', {}).get('teams', {}).get('buckets', [])

    # Constructing sentiment analysis result data structure
    team_sentiment = []
    for team_bucket in sentiment_buckets:
        time_series = [
            {
                "date": bucket['key_as_string'],
                "avg_sentiment": bucket['period_avg']['value'],
                "total_sentiment": bucket['period_total']['value'],
                "doc_count": bucket['doc_count']
            }
            for bucket in team_bucket['sentiment_over_time']['buckets']
            if bucket['doc_count'] > 0 # Filter time periods with no data
        ]
        team_sentiment.append({
            "name": team_bucket['key'],
            "mapped_name": TEAM_MAPPING.get(team_bucket['key'], team_bucket['key']),
            "total_sentiment": team_bucket['total_sentiment']['value'],
            "avg_sentiment": team_bucket['avg_sentiment']['value'],
            "doc_count": team_bucket['doc_count']['value'],
            "time_series": time_series
        })

    sorted_teams = sorted(team_sentiment, key=lambda x: x["total_sentiment"], reverse=True)
    top_5_teams = sorted_teams[:5]
    bottom_5_teams = sorted_teams[-5:]
    selected_teams = top_5_teams + bottom_5_teams

    # Query2: Get the subscribers from reddit data
    team_keys = [t["mapped_name"] for t in selected_teams] # Get the list of teams whose subscriber data we want to query

    subscribers_query = {
        "size": 1000,
        "fields": ["team", "subscribers", "retrieveDate"], # Return these three fields
        "query": {
            "bool": {
                "must": [
                    {"terms": {"team.keyword": team_keys}},
                    {"range": {"retrieveDate.keyword": {"gte": "2025-05-01"}}}
                ]
            }
        },
        "sort": [{"retrieveDate.keyword": {"order": "asc"}}] # Sort by date in ascending order
    }

    current_app.logger.info('Executing AFL team subscriber reddit count query')

    subs_result = es_client.search(index="afl-fans*", body=subscribers_query)

    # Processing subscribers data
    subs_docs = []
    for hit in subs_result["hits"]["hits"]:
        fields = hit.get("fields", {})
        subs_docs.append({
            "team": fields["team"][0],
            "subscribers": fields["subscribers"][0],
            "date": fields["retrieveDate"][0]
        })

    # Constructing time series data grouped by team
    subs_time_series = {}
    latest_subs = {}
    for doc in subs_docs:
        team = doc["team"]
        if team not in subs_time_series:
            subs_time_series[team] = []
        subs_time_series[team].append({"date": doc["date"], "subscribers": doc["subscribers"]})
        latest_subs[team] = doc["subscribers"]

    return {
        "sentiment_time_series": {
            "top_5": top_5_teams,
            "bottom_5": bottom_5_teams
        },
        "subscribers_time_series": subs_time_series,
        "latest_subscribers": latest_subs,
        "team_mapping": TEAM_MAPPING
    }
