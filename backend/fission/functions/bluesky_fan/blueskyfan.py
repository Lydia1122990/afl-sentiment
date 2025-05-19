import httpx
from datetime import datetime
import json
import requests
from flask import current_app

def addElastic(docID, indexText, doc):
    """
    Send data to Fission function 'addelastic' to store into Elasticsearch.
    """
    print("=== addElastic start ===", flush=True)
    url = 'http://router.fission/addelastic'
    payload = {"indexDocument": indexText, "docID": docID, "doc": doc}
    try:
        response = requests.post(url, json=payload, timeout=5)
        current_app.logger.info(f'=== aflBluesky: AddElastic : Response: {response.status_code} {response.text} ===')
    except Exception as e:
        current_app.logger.info(f'=== aflBluesky: AddElastic : Exception in addElastic POST: {str(e)} ===')
    return "ok"

def main():
    current_app.logger.info(f'=== aflBluesky: Initialise ===')

    # Load Bluesky credentials
    with open("/secrets/default/elastic-secret/BLUESKY_CLIENT_ID") as f:
        username = f.read().strip()
    with open("/secrets/default/elastic-secret/BLUESKY_CLIENT_PASSWORD") as f:
        password = f.read().strip()

    # Login to Bluesky to get JWT
    try:
        login_resp = httpx.post(
            "https://bsky.social/xrpc/com.atproto.server.createSession",
            json={"identifier": username, "password": password},
            timeout=10
        )
        login_resp.raise_for_status()
        session_data = login_resp.json()
        access_jwt = session_data["accessJwt"]
    except Exception as e:
        current_app.logger.info(f"aflBluesky: Bluesky login failed: {e}")
        return "error"

    # AFL Bluesky handles
    afl_teams_bsky = {
        "adelaidecrows": "adelaidefc.bsky.social",
        "brisbanelions": "brisbanelions.bsky.social",
        "carltonfc": "carltonfcblues.bsky.social",
        "collingwoodfc": "kristin542.bsky.social",
        "essendonfc": "essendonfc.bsky.social",
        "geelongcats": "ktsav99.bsky.social",
        "goldcoastsuns": "goldcoastsuns.bsky.social",
        "gws": "gwsgiants.bsky.social",
        "hawthorn": "hawksinsiders.bsky.social",
        "melbourne": "melbournefc.bsky.social",
        "northmelbourne": "nmfc.bsky.social",
        "portadelaide": "portadelaidefc.bsky.social",
        "stkilda": "stkildafc.bsky.social",
        "sydneyswans": "sydneyswansfcfan.bsky.social",
        "westcoasteagles": "westcoasteaglesfc.bsky.social",
        "westernbulldogs": "westernbulldogs.bsky.social",
        "richmond": "rhettrospective.bsky.social",
        "fremantle": "docker99.bsky.social"
    }

    headers = {"Authorization": f"Bearer {access_jwt}"}

    try:
        for team, handle in afl_teams_bsky.items():
            profile_resp = httpx.get(
                "https://bsky.social/xrpc/app.bsky.actor.getProfile",
                params={"actor": handle},
                headers=headers,
                timeout=10
            )
            profile_resp.raise_for_status()
            profile = profile_resp.json()

            followers = profile.get("followersCount", 0)
            retrieve_date = datetime.now().isoformat().replace(":", "-")
            doc_id = f"{team}_{retrieve_date}"
            doc = {
                "team": team,
                "followers": followers,
                "retrieved_at": retrieve_date
            }

            addElastic(doc_id, "afl-bluesky-fans", doc)
            print(f"✅ Sent {team}: {followers} followers")

        return "ok"

    except Exception as e:
        current_app.logger.info(f"aflBluesky: Error during processing: {e}")
        return "error"
