import logging
import json
from typing import Dict, Any, List
from flask import current_app, request
from elasticsearch8 import Elasticsearch

# fission package create --spec --name transportation-sentiment-reddit-pkg \
# --source ./transportation_sentiment_reddit/__init__.py \
# --source ./transportation_sentiment_reddit/transportation_sentiment_reddit.py \
# --source ./transportation_sentiment_reddit/requirements.txt \
# --source ./transportation_sentiment_reddit/build.sh \
# --env python39x --buildcmd './build.sh'

# fission fn create --spec --name transportation-sentiment-reddit \
# --pkg transportation-sentiment-reddit-pkg \
# --env python39x \
# --entrypoint "transportation_sentiment_reddit.main" \
# --specializationtimeout 180 \
# --secret elastic-secret 

# fission route create --spec --name transportation-sentiment-reddit \
# --function transportation-sentiment-reddit \
# --method GET \
# --url /transportation/sentiment/reddit \
# --createingress

# kubectl port-forward service/router -n fission 8080:80

# fission fn log -f --name transportation-sentiment-reddit
# curl -k http://localhost:8080/transportation/sentiment/reddit | jq

def main() -> Dict[str, Any]:
    """Calculate sentiment scores of transportation in different cities (average and total) from reddit from Elasticsearch
    
    Handles:
        - Connect to the Elasticsearch cluster
        - Perform an aggregation query to calculate the total sentiment score and average sentiment scores for each city
        - Find the city with the highest sentiment score and the city with the lowest sentiment score

    
    Returns:
        JSON response containing:
        - top_city_avg_reddit: The city with the highest avg sentiment
        - bottom_city_avg_reddit: The city with the lowest avg sentiment
        - all_cities_avg_reddit: all cities sorted by avg sentiment
        - top_city_total_reddit: The city with the highest total sentiment
        - bottom_city_total_reddit: The city with the lowest total sentiment
        - all_cities_total_reddit: all cities sorted by total sentiment
        - all_cities_count_reddit: total number of cities

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
        "query": {
            "bool": {
                "must_not": [
                    {"term": {"city.keyword": "melbournetrains"}}
                ]
            }
        },
        "aggs": {
            "cities_reddit": {
                "terms": {
                    "field": "city.keyword",
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

    current_app.logger.info('Executing sentiment scores of transportation in different cities from reddit analysis query')
    
    res: Dict[str, Any] = es_client.search(
        index='trans-reddit-sentiment*',  
        body=query_body
    )

   # Query result
    cities_data_reddit: List[Dict[str, Any]] = res.get('aggregations', {}).get('cities_reddit', {}).get('buckets', [])
        
    if not cities_data_reddit:
        return {'error': 'cannot find transportation-sentiment reddit data'}, 404
        
        
    all_cities_reddit = []
    for city_data_reddit in cities_data_reddit:
        all_cities_reddit.append({
            "name": city_data_reddit['key'],
            "total_sentiment_reddit": city_data_reddit['total_sentiment_reddit']['value'],
            "avg_sentiment_reddit": city_data_reddit['avg_sentiment_reddit']['value'],
            "doc_count_reddit": city_data_reddit['doc_count_reddit']['value']
        }) 

    # Sort by average-sentiment score and total-sentiment score
    sorted_cities_avg_reddit = sorted(all_cities_reddit, key=lambda x: x['avg_sentiment_reddit'])
    sorted_cities_total_reddit = sorted(all_cities_reddit, key=lambda x: x['total_sentiment_reddit'])

    highest_city_avg_reddit = sorted_cities_avg_reddit[-1] 
    lowest_city_avg_reddit = sorted_cities_avg_reddit[0] 
    highest_city_total_reddit = sorted_cities_total_reddit[-1] 
    lowest_city_total_reddit = sorted_cities_total_reddit[0] 


    return {
        'highest_city_avg_reddit': highest_city_avg_reddit,
        'lowest_city_avg_reddit': lowest_city_avg_reddit,
        'all_cities_avg_reddit': sorted_cities_avg_reddit,
        'highest_city_total_reddit': highest_city_total_reddit,
        'lowest_city_total_reddit': lowest_city_total_reddit,
        'all_cities_total_reddit': sorted_cities_total_reddit,
        'cities_count_reddit': len(sorted_cities_avg_reddit)
    }        
