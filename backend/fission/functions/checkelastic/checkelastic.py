from flask import current_app, request,jsonify
from elasticsearch8 import Elasticsearch 
from typing import Dict, List, Any
import json 
# fission package create --spec --name checkelastic-pkg --source ./functions/checkelastic/__init__.py --source ./functions/checkelastic/checkelastic.py --source ./functions/checkelastic/requirements.txt --source ./functions/checkelastic/build.sh --env python39 --buildcmd './build.sh'
# fission fn create --spec --name checkelastic --pkg checkelastic-pkg --env python39 --entrypoint checkelastic.main --specializationtimeout 180 --secret elastic-secret 

# fission route create --spec --name checkelastic-route --function checkelastic --url /checkelastic --method POST --createingress
 

def main():
    try:
        requestData: List[Dict[str, Any]] = request.get_json(force=True)
        
        current_app.logger.info(f'Processing {requestData["docID"]} - {requestData["indexDocument"]} observations')   

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
        return json.dumps({"found": bool(exists)})
    except Exception as e:
        print("Error in check elastic function ",str(e),flush=True)
        return {"error":str(e)},500
