import logging
import json
from typing import Dict, List, Any
from flask import current_app, request
from elasticsearch8 import Elasticsearch, ApiError

def main() -> str:
    """
    Recsive data, index and ID via HTTP and store data into elastic
    
    Handles:
    - Elasticsearch client initialization with security credentials through secrets
    - Suppression of SSL warnings for self-signed certificates
    - Document ID generation using ID
    - Save data into elasticsearch 

    Returns:
        'ok' on successful processing of all observations

    Raises:
        ApiError if elastic fails
    """
    # Initialize Elasticsearch client
    try:
        current_app.logger.info("=== addelastic: Elasticsearch client initialized ===") 

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
        
        requestData: List[Dict[str, Any]] = request.get_json(force=True) 

        # Index each observation
        docID: str = f'{requestData["docID"]}' 
        index_response: Dict[str, Any] = es.index(
            index=requestData["indexDocument"],
            id=docID,
            body=requestData["doc"]
        ) 
        current_app.logger.info(f'=== addelastic: Index response: {index_response} ===')
        current_app.logger.info(f'=== addelastic: Processing {requestData.get("indexDocument", "<missing index>")} ===')

    
        current_app.logger.info(
            f'Indexed {requestData.get("indexDocument")} {docID} - '
            f'Version: {index_response["_version"]}'
        )
        return 'ok'
    except ApiError as e:
        return json.dumps({"error": str(e)}), 500

    
