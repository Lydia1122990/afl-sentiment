import logging
import json
from typing import Dict, Any, List
from flask import current_app, request
from elasticsearch8 import Elasticsearch

# fission package create --spec --name transportation-sentiment-mastodon-pkg \
# --source ./transportation_sentiment_mastodon/__init__.py \
# --source ./transportation_sentiment_mastodon/transportation_sentiment_mastodon.py \
# --source ./transportation_sentiment_mastodon/requirements.txt \
# --source ./transportation_sentiment_mastodon/build.sh \
# --env python39x --buildcmd './build.sh'

# fission fn create --spec --name transportation-sentiment-mastodon \
# --pkg transportation-sentiment-mastodon-pkg \
# --env python39x \
# --entrypoint "transportation_sentiment_mastodon.main" \
# --specializationtimeout 180 \
# --secret elastic-secret 

# fission route create --spec --name transportation-sentiment-mastodon \
# --function transportation-sentiment-mastodon \
# --method GET \
# --url /transportation/sentiment/mastodon \
# --createingress

def main() -> Dict[str, Any]:
    """Calculate sentiment scores of transportation in different cities (average and total) from mastodon from Elasticsearch
    
    Handles:
        - Connect to the Elasticsearch cluster
        - Perform an aggregation query to calculate the total sentiment score and average sentiment scores for each city
        - Find the city with the highest sentiment score and the city with the lowest sentiment score

    
    Returns:
        JSON response containing:
        - top_city_avg_mastodon: The city with the highest avg sentiment
        - bottom_city_avg_mastodon: The city with the lowest avg sentiment
        - all_cities_avg_mastodon: all cities sorted by avg sentiment
        - top_city_total_mastodon: The city with the highest total sentiment
        - bottom_city_total_mastodon: The city with the lowest total sentiment
        - all_cities_total_mastodon: all cities sorted by total sentiment
        - all_cities_count_mastodon: total number of cities

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
            "cities_mastodon": {
                "terms": {
                    "field": "city",
                    "size": 100  
                },
                "aggs": {
                    "total_sentiment_mastodon": {"sum": {"field": "sentiment"}}, 
                    "avg_sentiment_mastodon": {"avg": {"field": "sentiment"}},
                    "doc_count_mastodon": {"value_count": {"field": "sentiment"}}
                }
            }
        }
    }

    current_app.logger.info('Executing sentiment scores of transportation in different cities from mastodon analysis query')
    
    res: Dict[str, Any] = es_client.search(
        index='mastodon_v2*',  
        body=query_body
    )

   # Query result
    cities_data_mastodon: List[Dict[str, Any]] = res.get('aggregations', {}).get('cities_mastodon', {}).get('buckets', [])
        
    if not cities_data_mastodon:
        return {'error': 'cannot find transportation-sentiment mastodon data'}, 404
        
        
    all_cities_mastodon = []
    for city_data_mastodon in cities_data_mastodon:
        all_cities_mastodon.append({
            "name": city_data_mastodon['key'],
            "total_sentiment_mastodon": city_data_mastodon['total_sentiment_mastodon']['value'],
            "avg_sentiment_mastodon": city_data_mastodon['avg_sentiment_mastodon']['value'],
            "doc_count_mastodon": city_data_mastodon['doc_count_mastodon']['value']
        }) 

    # Sort by average-sentiment score and total-sentiment score
    sorted_cities_avg_mastodon = sorted(all_cities_mastodon, key=lambda x: x['avg_sentiment_mastodon'])
    sorted_cities_total_mastodon = sorted(all_cities_mastodon, key=lambda x: x['total_sentiment_mastodon'])

    highest_city_avg_mastodon = sorted_cities_avg_mastodon[-1] 
    lowest_city_avg_mastodon = sorted_cities_avg_mastodon[0] 
    highest_city_total_mastodon = sorted_cities_total_mastodon[-1] 
    lowest_city_total_mastodon = sorted_cities_total_mastodon[0] 


    return {
        'highest_city_avg_mastodon': highest_city_avg_mastodon,
        'lowest_city_avg_mastodon': lowest_city_avg_mastodon,
        'all_cities_avg_mastodon': sorted_cities_avg_mastodon,
        'highest_city_total_mastodon': highest_city_total_mastodon,
        'lowest_city_total_mastodon': lowest_city_total_mastodon,
        'all_cities_total_mastodon': sorted_cities_total_mastodon,
        'cities_count_mastodon': len(sorted_cities_avg_mastodon)
    }        
