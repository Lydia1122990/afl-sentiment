"""
This is a unit test that tests the following functionality:
Is the Kubernetes Secret mount successfully read?
Is the connection with Elasticsearch normal?
Are the write permissions and index path configured correctly?
Can the Fission function run normally?
"""

def main():
    import requests
    es_user_path = "/secrets/default/elastic-secret-mastodon/ES_USERNAME"
    es_password_path = "/secrets/default/elastic-secret-mastodon/ES_PASSWORD"
    mastodon_token_path = "/secrets/default/elastic-secret-mastodon/MASTODON_ACCESS_TOKEN"
    try:
        with open(es_user_path, 'r') as f:
            es_username = f.read().strip()
        with open(es_password_path, 'r') as f:
            es_password = f.read().strip()
        with open(mastodon_token_path, 'r') as f:
            mastodon_token = f.read().strip()
    except Exception as e:
        print(f"Key acquisition failed: {e}")

    try:
        doc = {
            "platform": "Test Mastodon",
            "text": "Hello Unimelb!",
            "city": "Melbourne",
            "sentiment": 1,
            "url": "https://test.post.unimelb",
            "createdOn": "2025-05-08T00:00:00Z"
        }

        es_host = "https://elasticsearch-master.elastic.svc.cluster.local:9200/mastodon/_doc"
        es_auth = (es_username, es_password)

        res = requests.post(es_host, json=doc, auth=es_auth, verify=False)

        return {
            "Code": res.status_code,
            "message": "Elasticsearch Write Success" if res.status_code in [200, 201] else f"Writing failed: {res.text}"
        }

    except Exception as e:
        return {"Code": 500, "body": f"Exception: {e}"}