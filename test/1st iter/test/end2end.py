import unittest
import requests
import json
from unittest.mock import patch

class HTTPSession:
    """HTTP client session wrapper for making API requests.

    Attributes:
        session: Requests session object
        base_url: Base URL for API endpoints
    """
    
    def __init__(self, protocol: str, hostname: str, port: int) -> None:
        self.session = requests.Session()
        self.base_url = f'{protocol}://{hostname}:{port}' 
        
    def post(self, path: str, data=None):
        return self.session.post(f'{self.base_url}/{path}', json=data)

class TestEnd2End(unittest.TestCase):
    """End-to-end tests for student/course management API."""
    def testEnqueue(self): 
        self.assertEqual(
            testRequest.post("enqueue").status_code,
            200
        ) 

if __name__ == '__main__':

    testRequest = HTTPSession('http', 'localhost', 9090)
    unittest.main()
