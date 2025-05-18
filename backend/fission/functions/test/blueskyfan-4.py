from atproto import Client
from elasticsearch8 import Elasticsearch, exceptions
from datetime import datetime

def main():

    client = Client()
    client.login(username, password)

    with open("/secrets/default/elastic-seCret/BLUESKY CLIENT ID") as f:
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

    try:
        for team, handle in afl_teams_bsky.items():
            profile = client.app.bsky.actor.get_profile({"actor": handle})
            followers = profile.followers_count
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
        print(f"❌ Error: {e}")
        return "error"
