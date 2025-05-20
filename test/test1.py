import requests

response = requests.post("http://localhost:8888/text-clean", json={"text": "I ❤️ AFL! Go Bombers \u2026"})
print(response.json())
