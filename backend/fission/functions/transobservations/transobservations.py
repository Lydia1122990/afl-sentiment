import logging
import json
import requests
from flask import current_app
from typing import Dict, Any, Optional


def main() -> str:
    """
    Returns:
        str: 'OK' on successful harvest and enqueue

    Note:
        Uses IDV60901.95936 product code for Mildura Airport observations
    """
    response = requests.get(
        'http://reg.bom.gov.au/fwo/IDV60901/IDV60901.95936.json'
    )
    response.raise_for_status()

    # Logs harvesting
    current_app.logger.info(f'Harvested transport observations')

    # Route to message queue
    response: Optional[requests.Response] = requests.post(
        url='http://router.fission/enqueue/CITY',
        headers={'Content-Type': 'application/json'},
        json=response.json()
    )

    return 'OK'
