import requests
import json
def test_transHarvester(self): 
        response = testRequest.post(
            "transHarvester",
            json={"city": "melbourne", "limit": 10}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("ok", response.text)