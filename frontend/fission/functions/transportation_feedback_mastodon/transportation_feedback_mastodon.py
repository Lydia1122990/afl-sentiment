import logging
from typing import Dict, Any, List
from flask import current_app
from elasticsearch8 import Elasticsearch
from collections import Counter
import re

def main() -> Dict[str, Any]:
    """Analyse most mentioned feedback terms by city from Mastodon in Elasticsearch
    
    Returns:
        JSON response containing:
        - top_feedback: Top 10 feedback terms across all data
        - city_feedback: Dictionary with cities as keys and their top 5 feedback terms
    """

    # Elasticsearch connection
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

    # Feedback terms to analyse
    feedback_terms = [
        'slow', 'late', 'delay', 'delayed', 'crowd', 'crowded', 'full', 'packed',
        'expensive', 'cheap','price', 'dirty', 'clean', 'broken', 
        'smell', 'noisy', 'loud', 'hot', 'cold', 'old', 'new', 'safe', 'dangerous',
        'reliable', 'unreliable', 'frequent', 'infrequent', 'comfortable', 'uncomfortable', 
        'maintenance', 'cancel', 'cancelled', 'strike', 'breakdown', 'accident'
    ]

    # Query to get text data grouped by city
    query_body: Dict[str, Any] = {
        "size": 0,
        "aggs": {
            "cities": {
                "terms": {
                    "field": "city",
                    "size": 100  # Get all cities
                },
                "aggs": {
                    "text_samples": {
                        "top_hits": {
                            "size": 100,  # Get 100 sample texts per city
                            "_source": ["text"]
                        }
                    }
                }
            }
        }
    }

    current_app.logger.info('Executing feedback analysis query')
    
    res: Dict[str, Any] = es_client.search(
        index='mastodon_v2*',
        body=query_body
    )

    # Process results
    cities_data: List[Dict[str, Any]] = res.get('aggregations', {}).get('cities', {}).get('buckets', [])
    
    if not cities_data:
        return {'error': 'No feedback data found'}, 404
    
    city_feedback = {}
    all_feedback_terms = []
    
    for city_data in cities_data:
        city_name = city_data['key']
        text_samples = [hit['_source']['text'] for hit in city_data['text_samples']['hits']['hits']]
        
        # Extract and count feedback terms
        feedback_terms_found = []
        for text in text_samples:
            text_lower = text.lower()
            for term in feedback_terms:
                if re.search(r'\b' + re.escape(term) + r'\b', text_lower):
                    feedback_terms_found.append(term)
        
        # Get top 5 most common feedback terms for this city
        term_counter = Counter(feedback_terms_found)
        top_terms = term_counter.most_common(5)
        
        city_feedback[city_name] = {
            'top_terms': top_terms,
            'total_mentions': sum(term_counter.values())
        }
        
        all_feedback_terms.extend(feedback_terms_found)
    
    # Get overall most common feedback terms
    overall_counter = Counter(all_feedback_terms)
    top_feedback = overall_counter.most_common(10)
    
    return {
        'top_feedback': top_feedback,
        'city_feedback': city_feedback
    }