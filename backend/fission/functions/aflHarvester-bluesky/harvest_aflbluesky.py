import httpx
from datetime import datetime
import json
import requests
from flask import current_app
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from nltk.tokenize import sent_tokenize
import nltk
nltk.download('punkt_tab')  # Download tokenizer data for sentence splitting

sentimentAnalyser = SentimentIntensityAnalyzer()

# Team nicknames for matching
TEAM = {
    "adelaidefc": ["adelaide crows", "crows", "crows reserves", "whites", "white noise", "kuwarna"],
    "brisbanelions": ["brisbane lions", "maroons", "gorillas", "lions"],
    "carltonblues": ["carlton", "blues", "blue baggers", "baggers", "old navy blues"],
    "collingwoodfc": ["collingwood", "magpies", "pies", "woods", "woodsmen"],
    "essendonfc": ["essendon", "bombers", "dons", "same olds"],
    "fremantlefc": ["fremantle", "dockers", "freo", "walyalup"],
    "geelongcats": ["geelong", "cats"],
    "gcfc": ["gold coast suns", "suns", "sunnies", "coasters"],
    "gwsgiants": ["gws giants", "greater western sydney giants", "giants", "gws", "orange team"],
    "hawktalk": ["hawthorn", "hawks"],
    "melbournefc": ["melbourne", "demons", "dees", "narrm", "redlegs", "fuchsias"],
    "northmelbournefc": ["north melbourne", "kangaroos", "kangas", "roos", "north", "shinboners"],
    "weareportadelaide": ["port adelaide", "power", "port", "cockledivers", "seaside men", "seasiders", "magentas", "portonians", "ports"],
    "richmondfc": ["richmond", "tigers", "tiges", "fighting fury"],
    "stkilda": ["st kilda", "saints", "sainters"],
    "sydneyswans": ["sydney swans", "swans", "swannies", "bloods"],
    "westcoasteagles": ["west coast eagles", "eagles"],
    "westernbulldogs": ["western bulldogs", "dogs", "doggies", "scraggers", "the scray", "footscray", "tricolours"]
}

# Create a reverse mapping from nickname to team ID
teamNickname = {}
for team, nicknames in TEAM.items():
    for alias in nicknames:
        teamNickname[alias.lower()] = team

# Clean text via Fission service
def cleanText(text) -> str:
    url = 'http://router.fission/text-clean'
    payload = {"text": text}
    response = requests.post(url, json=payload)
    return response.json()["cleanedText"]

# Identify which teams are mentioned in the text
def teamMentioned(text, teams=teamNickname) -> list:
    foundTeam = set()
    for nickname, team in teams.items():
        if nickname in text.lower():
            foundTeam.add(team)
    return list(foundTeam)

# Perform sentiment analysis per team based on sentence-level matches
def sentimentPerTeam(text):
    sentences = sent_tokenize(text)
    teamSentiment = {team: [] for team in TEAM}

    for sentence in sentences:
        sentiment = sentimentAnalyser.polarity_scores(sentence)['compound']
        for team, nicknames in TEAM.items():
            if any(nick in sentence.lower() for nick in nicknames):
                teamSentiment[team].append(sentiment)

    result = {}
    for team, values in teamSentiment.items():
        if values:
            result[team] = round(sum(values) / len(values), 3)
    return result  

# Check if a document already exists in Elasticsearch
def checkPost(docID):
    url = 'http://router.fission/checkelastic'
    payload = {"indexDocument": "afl_bluesky_sentiment-18", "docID": docID}
    try:
        res = requests.post(url, json=payload, timeout=5)
        return res.json().get("found", False)
    except Exception as e:
        current_app.logger.info(f"aflBluesky: checkPost error: {e}")
        return False

# Add a document to Elasticsearch
def addElastic(docID, indexText, doc):
    payload = {"indexDocument": indexText, "docID": docID, "doc": doc}
    current_app.logger.info(f'=== aflBluesky: AddElastic : Payload: {json.dumps(payload)} ===')
    url = 'http://router.fission/addelastic'
    try:
        response = requests.post(url, json=payload, timeout=5)
        current_app.logger.info(f'=== aflBluesky: AddElastic : Response: {response.status_code} {response.text} ===')
    except Exception as e:
        current_app.logger.info(f'=== aflBluesky: AddElastic : Exception in addElastic POST: {str(e)} ===')
    return "ok"

# Convert Bluesky URI to public URL
def convertUriToUrl(uri: str) -> str:
    if uri.startswith("at://"):
        try:
            user, postid = uri.replace("at://", "").split("/app.bsky.feed.post/")
            return f"https://bsky.app/profile/{user}/post/{postid}"
        except:
            return uri
    return uri

# Search and process Bluesky posts for a given keyword
def harvestByKeyword(keyword, headers):
    try:
        resp = httpx.get(
            "https://bsky.social/xrpc/app.bsky.feed.searchPosts",
            params={"q": keyword, "limit": 100},
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        feed = resp.json()

        for post in feed.get("posts", []):
            record = post.get("record", {})
            text = cleanText(record.get("text", ""))
            created = record.get("createdAt", datetime.now().isoformat())
            uri = post.get("uri", "")
            url = convertUriToUrl(uri)
            upvote = post.get("likeCount", 1)
            if not isinstance(upvote, int) or upvote == 0:
                upvote = 1

            teams = teamMentioned(text)
            if not teams:
                continue  # Skip if no team mentioned

            sentiments = sentimentPerTeam(text)
            for team in teams:
                if team in sentiments:
                    doc_id = f"{uri}_{team}".lower()
                    if checkPost(doc_id):
                        current_app.logger.info(f"Skipped {doc_id} as it exists")
                        continue
                    doc = {
                        "type": "post",
                        "platform": "Bluesky",
                        "team": team,
                        "sentiment": sentiments[team],
                        "text": text,
                        "upvote": upvote,
                        "createdOn": created,
                        "url": url
                    }
                    addElastic(doc_id, "afl_bluesky_sentiment-18", doc)

    except Exception as e:
        current_app.logger.info(f"aflBluesky: Error in harvestByKeyword for '{keyword}': {e}")
        return "error"

# Main function to run the whole harvesting process
def main():
    current_app.logger.info(f'=== aflBluesky: Initialise ===')

    # Read Bluesky credentials
    with open("/secrets/default/elastic-secret/BLUESKY_CLIENT_ID") as f:
        username = f.read().strip()
    with open("/secrets/default/elastic-secret/BLUESKY_CLIENT_PASSWORD") as f:
        password = f.read().strip()

    try:
        # Login to Bluesky to get access token
        login_resp = httpx.post(
            "https://bsky.social/xrpc/com.atproto.server.createSession",
            json={"identifier": username, "password": password},
            timeout=10
        )
        login_resp.raise_for_status()
        access_jwt = login_resp.json()["accessJwt"]
    except Exception as e:
        current_app.logger.info(f"aflBluesky: Bluesky login failed: {e}")
        return "error"

    headers = {"Authorization": f"Bearer {access_jwt}"}

    # Iterate over all nicknames to harvest matching posts
    for team, nicknames in TEAM.items():
        for keyword in nicknames:
            harvestByKeyword(keyword, headers=headers)

    return "ok"
