import logging
from typing import Dict, Any, List
from flask import current_app
from elasticsearch8 import Elasticsearch

# fission package create --spec --name transportation-post-comparison-pkg \
# --source ./transportation_post_comparison/__init__.py \
# --source ./transportation_post_comparison/transportation_post_comparison.py \
# --source ./transportation_post_comparison/requirements.txt \
# --source ./transportation_post_comparison/build.sh \
# --env python39x --buildcmd './build.sh'

# fission fn create --spec --name transportation-post-comparison \
# --pkg transportation-post-comparison-pkg \
# --env python39x \
# --entrypoint "transportation_post_comparison.main" \
# --specializationtimeout 180 \
# --secret elastic-secret 
# 
# fission route create --spec --name transportation-post-comparison \
# --function transportation-post-comparison \
# --method GET \
# --url /transportation/post/comparison \
# --createingress

# kubectl port-forward service/router -n fission 8080:80

# fission fn log -f --name transportation-post-comparison
# curl -k http://localhost:8080/transportation/post/comparison | jq

def main() -> Dict[str, Any]:
    """Compare transportation sentiment between Mastodon and Reddit
    
    Returns:
        JSON response containing:
        - total_posts: Total posts count for each platform
        - city_comparison: List of cities with post counts and sentiment for both platforms
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
    # Mastodon query
    mastodon_query = {
        "size": 0,
        "aggs": {
            "cities": {
                "terms": {"field": "city", "size": 100},
                "aggs": {
                    "total_sentiment": {"sum": {"field": "sentiment"}},
                    "avg_sentiment": {"avg": {"field": "sentiment"}},
                    "doc_count": {"value_count": {"field": "sentiment"}}
                }
            },
            "total_posts": {"value_count": {"field": "sentiment"}}
        }
    }

    # Reddit query (excluding melbournetrains)
    reddit_query = {
        "size": 0,
        "query": {
            "bool": {
                "must_not": [{"term": {"city.keyword": "melbournetrains"}}]
            }
        },
        "aggs": {
            "cities": {
                "terms": {"field": "city.keyword", "size": 100},
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
    current_app.logger.info('Executing Mastodon and Reddit queries')
    mastodon_res = es_client.search(index='mastodon_v2*', body=mastodon_query)
    reddit_res = es_client.search(index='trans-reddit-sentiment*', body=reddit_query)
    
    # Process data
    mastodon_cities = process_city_data(mastodon_res, 'mastodon')
    mastodon_total = mastodon_res['aggregations']['total_posts']['value']
    
    reddit_cities = process_city_data(reddit_res, 'reddit')
    reddit_total = reddit_res['aggregations']['total_posts']['value']
    
    # Merge data
    city_comparison = merge_city_data(mastodon_cities, reddit_cities)

    return {
        'total_posts': {
            'mastodon': mastodon_total,
            'reddit': reddit_total
        },
        'city_comparison': city_comparison
    }

# Process city data from Elasticsearch response
def process_city_data(res: Dict[str, Any], platform: str) -> List[Dict[str, Any]]:
    cities_data = res.get('aggregations', {}).get('cities', {}).get('buckets', [])
    return [{
        "name": city['key'],
        "total_sentiment": city['total_sentiment']['value'],
        "avg_sentiment": city['avg_sentiment']['value'],
        "doc_count": city['doc_count']['value']
    } for city in cities_data]

# Merge data from both platforms for each city
def merge_city_data(mastodon_data: List[Dict[str, Any]], reddit_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    all_cities = set(city['name'] for city in mastodon_data) | set(city['name'] for city in reddit_data)
    
    merged = []
    for city in all_cities:
        mastodon = next((c for c in mastodon_data if c['name'] == city), None)
        reddit = next((c for c in reddit_data if c['name'] == city), None)
        
        merged.append({
            'name': city,
            'mastodon_posts': mastodon['doc_count'] if mastodon else 0,
            'mastodon_avg_sentiment': mastodon['avg_sentiment'] if mastodon else 0,
            'mastodon_total_sentiment': mastodon['total_sentiment'] if mastodon else 0,
            'reddit_posts': reddit['doc_count'] if reddit else 0,
            'reddit_avg_sentiment': reddit['avg_sentiment'] if reddit else 0,
            'reddit_total_sentiment': reddit['total_sentiment'] if reddit else 0
        })
    
    return sorted(merged, key=lambda x: x['mastodon_posts'] + x['reddit_posts'], reverse=True)