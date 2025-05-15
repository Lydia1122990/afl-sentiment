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

    def get(self, path: str) -> requests.Response:
        """Send GET request to specified path."""
        return self.session.get(f'{self.base_url}/{path}')

    def post(self, path: str, data: dict=None, json=None) -> requests.Response:
        """Send POST request with data to specified path."""
        return self.session.post(f'{self.base_url}/{path}', json=data)

    def put(self, path: str, data: dict) -> requests.Response:
        """Send PUT request with data to specified path."""
        return self.session.put(f'{self.base_url}/{path}', data)

    def delete(self, path: str) -> requests.Response:
        """Send DELETE request to specified path."""
        return self.session.delete(f'{self.base_url}/{path}')



class TestEnd2End(unittest.TestCase):
    """End-to-end tests for the Fission `text-clean` function.""" 
    def test_textclean_status_code(self):
        self.assertEqual(
            testRequest.post("text-clean", {"text": "GO BAGGERS!! 💪"}).status_code,
            200
        )

    def test_textclean_response_body(self):
        self.assertIn(
            "baggers",
            testRequest.post("text-clean", {"text": "GO BAGGERS!! 💪"}).text.lower()
        )

    def test_textclean_removes_emoji(self):
        response = testRequest.post("text-clean", {"text": "🏉 footy time"})
        self.assertNotIn("🏉", response.text)

    def test_textclean_handles_empty_input(self):
        response = testRequest.post("text-clean", {"text": ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.text)["cleanedText"], "")
        
    def test_textclean_specialchar(self):
        response = testRequest.post("text-clean", {"text": "\u2014 \u2014 Winner\u2026"}) 
        self.assertEqual(json.loads(response.text)["cleanedText"], "— — Winner...")
    def test_enqueue(self): 
        response = testRequest.post(
            "enqueue/test",
            json={"team": "melbournefc", "limit": 10}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("ok", response.text)
        
    def test_elastic(self):
        payload = {
            "index": "test-log",
            "indexDocument": "test-log",
            "docID": "test1",
            "doc": {
                "team": "gws",
                "sentiment": 0.45, 
                "timestamp": "2025-05-16T11:11:11Z"
            }
        }
        self.assertEqual(testRequest.post("addelastic",payload).status_code,200) 
        self.assertIn("ok", testRequest.post("addelastic",payload).text.lower())
        
        

if __name__ == '__main__':

    testRequest = HTTPSession('http', 'localhost', 9090)
    unittest.main()
