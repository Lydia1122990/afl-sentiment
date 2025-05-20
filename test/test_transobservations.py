import requests
import json
def test_transobservations(self): 
        response = testRequest.post(
            "transobservations",
            json={"city": "melbourne", "limit": 10}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("ok", response.text)