from flask import current_app, request,jsonify
from elasticsearch8 import Elasticsearch 
from typing import Dict, List, Any
import json  

def main():
    """
    Check elasticsaerch databse to see if ID exisit if so return True else return False
    """
    try:
        requestData: List[Dict[str, Any]] = request.get_json(force=True)
        
        current_app.logger.info(f'=== checkelast: Processing {requestData["docID"]} - {requestData["indexDocument"]} ===')   

        if not requestData["docID"]:
            return "Missing index ID parameter", 400
        # Initialize Elasticsearch client
        with open("/secrets/default/elastic-secret/ES_USERNAME") as f:
            es_username = f.read().strip()

        with open("/secrets/default/elastic-secret/ES_PASSWORD") as f:
            es_password = f.read().strip() 
            
        es: Elasticsearch = Elasticsearch(
            'https://elasticsearch-master.elastic.svc.cluster.local:9200',
            verify_certs=False,
            ssl_show_warn=False,
            basic_auth=(es_username, es_password)
        ) 
        exists = es.get(index=requestData["indexDocument"], id=requestData["docID"])
        current_app.logger.info(
                    f'=== checkelast: ID found in {requestData["indexDocument"]} ===' 
                )
        return json.dumps({"found": bool(exists)})
    except Exception as e: 
        current_app.logger.info(
                    f'=== checkelastic:Error in searching for ID in {requestData["indexDocument"]} ==='
                    f'=== checkelastic:ID not found ===' 
                )
        return json.dumps({"found": False})
