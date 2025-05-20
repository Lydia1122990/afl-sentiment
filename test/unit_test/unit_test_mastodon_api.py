"""
This function is used to read the Mastodon Access 
Token from the Kubernetes Secret and 
then call the Mastodon /verify_credentials 
interface to verify whether the token is valid.

This is a unit test that tests the following functionality:

Is the Secret correctly mounted?
Is the access Token correctly read?
Does the Token have permission to access Mastodon?
Can the network request successfully reach the instance (such as mastodon.social)

"""
import os
import requests

def main():
    try:
        with open('/secrets/default/elastic-secret-mastodon/MASTODON_ACCESS_TOKEN', 'r') as f:
            mastodon_token = f.read().strip()

        mastodon_url = "https://mastodon.social/api/v1/accounts/verify_credentials"

        headers = {
            "Authorization": f"Bearer {mastodon_token}"
        }

        response = requests.get(mastodon_url, headers=headers)

        if response.status_code == 200:
            account = response.json()
            return {
                "Code": 200,
                "message": f"Token Valid! Logged in as: {account['username']}"
            }
        else:
            return {
                "Code": response.status_code,
                "message": f"Token Invalid: {response.text}"
            }

    except Exception as e:
        return {
            "Code": 500,
            "message": f"Exception occurred: {str(e)}"
        }
