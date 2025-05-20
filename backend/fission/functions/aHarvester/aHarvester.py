import logging
import json
import requests
from flask import current_app
from typing import Dict, Any, Optional 

def main() -> str:
    """
    Performs: 
    - Logs successful harvest operation
    - Trigger enqueue function via Fission router

    Returns:
        str: 'OK' on successful harvest and enqueue
 
    """  
    current_app.logger.info(f'=== aHarvester: Trigger enqueue for AFL Harvester ===') 
    response: Optional[requests.Response] = requests.post(
        url='http://router.fission/enqueue/TEAM',
        headers={'Content-Type': 'application/json'}, 
    )

    return 'OK'
