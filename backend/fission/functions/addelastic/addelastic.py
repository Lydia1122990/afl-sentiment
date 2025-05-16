import logging
import json
from typing import Dict, List, Any
from flask import current_app, request
from elasticsearch8 import Elasticsearch

# fission package create --spec --name elastic-pkg --source ./functions/addelastic/addelastic.py --source ./functions/addelastic/requirements.txt --env python39 
# fission fn create --spec --name addelastic --pkg elastic-pkg --env python39 --entrypoint addelastic.main --specializationtimeout 180 --secret elastic-secret 
# fission route create --spec --name addelastic-route --function addelastic --url /addelastic --method POST --createingress
 


def main() -> str:
    """Process and index weather observation data into Elasticsearch.

    Handles:
    - Elasticsearch client initialization with security credentials through secrets
    - Suppression of SSL warnings for self-signed certificates
    - Bulk indexing of observation records
    - Document ID generation using station ID and timestamp
    - Request payload validation and logging

    Returns:
        'ok' on successful processing of all observations

    Raises:
        JSONDecodeError: If invalid JSON payload received
        ElasticsearchException: For indexing failures
    """
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

    # Validate and parse request payload
    requestData: List[Dict[str, Any]] = request.get_json(force=True)
    current_app.logger.info(f'Processing {requestData["index"]} observations')

    # Index each observation
    docID: str = f'{requestData["docID"]}' 

    index_response: Dict[str, Any] = es.index(
        index=requestData["indexDocument"],
        id=docID,
        body=requestData["doc"]
    )

    current_app.logger.info(
        f'Indexed {requestData["index"]} {docID} - '
        f'Version: {index_response["_version"]}'
    )

    return 'ok'
