"""
This is a test function for debugging whether the Kubernetes Secret is mounted correctly.

This is a unit test that tests the following functionality:

Whether the Secret path /secrets/default/elastic-secret-mastodon/ES_USERNAME exists;
Whether the function has the permission to read the path;
Whether the file content is read correctly;
Whether the function can return the result to the caller.
"""
def main():
    token_path = "/secrets/default/elastic-secret-mastodon/ES_USERNAME"
    try:
        with open(token_path, 'r') as f:
            elastic_token = f.read().strip()
    except Exception as e:
        elastic_token = f"Error access token: {e}"

    return {
        "Code": 200,
        "messsage": f"Token is: {elastic_token}"
    }
