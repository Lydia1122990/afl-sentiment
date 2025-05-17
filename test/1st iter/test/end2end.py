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
    
    def get(self, path: str) -> requests.Response:
        """Send GET request to specified path."""
        return self.session.get(f'{self.base_url}/{path}')

    def put(self, path: str, data: dict) -> requests.Response:
        """Send PUT request with data to specified path."""
        return self.session.put(f'{self.base_url}/{path}', data)

    def delete(self, path: str) -> requests.Response:
        """Send DELETE request to specified path."""
        return self.session.delete(f'{self.base_url}/{path}')

class TestEnd2End(unittest.TestCase):
    """End-to-end tests for student/course management API."""
    # def testEnqueue(self): 
    #     self.assertEqual(
    #         testRequest.post("enqueue/TEAM").status_code,
    #         200
    #     )
    # def testElastic(self):
    #     payload = {
    #         "index": "afl-sentiment",
    #         "indexDocument": "afl-sentiment",
    #         "docID": "test-team-2024",
    #         "doc": {
    #             "team": "gws",
    #             "sentiment": 0.45, 
    #         }
    #     }
    #     self.assertEqual(testRequest.post("addelastic",payload).status_code,200)  
        
    def testCheckElastic(self):
        payload = {
            "indexDocument": "trans-reddit-sentiment",
            "docID": "1knwsm1_melbournetrains_post", 
        }
        self.assertEqual(testRequest.post("checkelastic",payload).status_code,200) 
        
if __name__ == '__main__':

    testRequest = HTTPSession('http', 'localhost', 9090)
    unittest.main()
