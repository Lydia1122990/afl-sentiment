import httpx
from elasticsearch8 import Elasticsearch, exceptions
from datetime import datetime
import json

print("import done")

def main():
    # Load Bluesky credentials from secrets
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
        did = session_data["did"]
    except Exception as e:
        print(f"❌ Bluesky login failed: {e}")
        return "error"

    # Load Elasticsearch credentials from secrets
    with open("/secrets/default/elastic-secret/ES_USERNAME") as f:
        es_username = f.read().strip()
    with open("/secrets/default/elastic-secret/ES_PASSWORD") as f:
        es_password = f.read().strip()

    es = Elasticsearch(
        hosts=["https://elasticsearch-master.elastic.svc.cluster.local:9200"],
        basic_auth=(es_username, es_password),
        verify_certs=False,
        ssl_show_warn=False
    )

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
            # Get profile via HTTP
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

            es.create(index="afl-bluesky-fans", id=doc_id, document=doc)
            print(f"✅ Indexed {team}: {followers} followers")

        return "ok"

    except exceptions.ConflictError:
        print("⚠️ Document already exists, skipping...")
        return "ok"
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        return "error"
