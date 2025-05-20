import logging
from typing import Dict, Any, List
from flask import current_app
from elasticsearch8 import Elasticsearch
from collections import Counter
import re

def main() -> Dict[str, Any]:
    """Analyse most mentioned feedback terms by team from afl-sentiment index
    
    Returns:
        JSON response containing:
        - top_feedback: Top 15 feedback terms across all data
        - team_feedback: Dictionary with teams as keys and their top 5 feedback terms
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
        # Common player roles/positions
        'forward', 'defender', 'midfielder', 'ruckman', 'wingman', 'halfback',
        'halfforward', 'fullback', 'fullforward', 'captain',
        # Actions and events
        'kicked', 'marked', 'tackled', 'passed', 'scored', 'leading', 'trailing',
        'comeback', 'upset', 'thriller', 'blowout', 'intercepted', 'bounced',
        'shepherded', 'smothered', 'spoiled',
        # Sentiment related (can be combined with team/player names)
        'good', 'bad', 'great', 'terrible', 'love', 'hate', 'proud', 'disappointed',
        'excited', 'nervous', 'happy', 'sad', 'angry', 'amazing', 'awful', 'fantastic',
        'rubbish', 'suck', 'sucks', 'brilliant', 'excellent', 'support', 'unfair',
        'frustrating', 'poor', 'deserved', 'undeserved', 'thrilled', 'gutted', 'fuming',
        'joyful', 'hopeless', 'confident', 'worried', 'pumped', 'devastated',
        'elated', 'bitter', 'smug', 'relieved',
        # Specific game elements
        'clearance', 'inside50', 'possession', 'contest', 'stoppage', 'rebound',
        'setshot', 'snap', 'boundary', 'wing', 'centre', 'arc'
    ]

    # Query to get text data grouped by team
    query_body: Dict[str, Any] = {
        "size": 0,
        "aggs": {
            "teams": {
                "terms": {
                    "field": "team.keyword",
                    "size": 100
                },
                "aggs": {
                    "text_samples": {
                        "top_hits": {
                            "size": 100, # limit is 100
                            "_source": ["text"]
                        }
                    }
                }
            }
        }
    }

    current_app.logger.info('Executing AFL sentiment feedback analysis query')
    
    res: Dict[str, Any] = es_client.search(
        index='afl-sentiment',
        body=query_body
    )

    # Process results
    teams_data: List[Dict[str, Any]] = res.get('aggregations', {}).get('teams', {}).get('buckets', [])
    
    if not teams_data:
        return {'error': 'No AFL feedback data found'}, 404
    
    team_feedback = {}
    all_feedback_terms = []
    
    for team_data in teams_data:
        team_name = team_data['key']
        text_samples = [hit['_source']['text'] for hit in team_data['text_samples']['hits']['hits']]
        
        # Extract and count feedback terms
        feedback_terms_found = []
        for text in text_samples:
            text_lower = text.lower()
            for term in feedback_terms:
                if re.search(r'\b' + re.escape(term) + r'\b', text_lower):
                    feedback_terms_found.append(term)
        
        # Get top 5 most common feedback terms for this team
        term_counter = Counter(feedback_terms_found)
        top_terms = term_counter.most_common(5)
        
        team_feedback[team_name] = {
            'top_terms': top_terms,
            'total_mentions': sum(term_counter.values())
        }
        
        all_feedback_terms.extend(feedback_terms_found)
    
    # Get overall most common feedback terms
    overall_counter = Counter(all_feedback_terms)
    top_feedback = overall_counter.most_common(15)
    
    return {
        'top_feedback': top_feedback,
        'team_feedback': team_feedback
    }