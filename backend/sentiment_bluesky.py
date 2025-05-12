import os
import time
import emoji
import requests
from dotenv import load_dotenv
from atproto import Client, models
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from nltk.tokenize import sent_tokenize
import nltk
from datetime import datetime

nltk.download('punkt')

# Load environment variables - test
load_dotenv()

# AFL teams and nicknames
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
    "westernbulldogs": ["western bulldogs", "dogs", "doggies", "scraggers", "the scray", "footscray", "tricolours"],
    "tasmanianafl": ["tasmania football club", "devils", "tassie"]
}

def get_afl_teams():
    return [
        'Adelaide Crows', 'Brisbane Lions', 'Carlton Blues', 
        'Collingwood Magpies', 'Essendon Bombers', 'Fremantle Dockers',
        'Geelong Cats', 'Gold Coast Suns', 'GWS Giants', 'Hawthorn Hawks',
        'Melbourne Demons', 'North Melbourne Kangaroos', 'Port Adelaide Power',
        'Richmond Tigers', 'St Kilda Saints', 'Sydney Swans',
        'West Coast Eagles', 'Western Bulldogs'
    ]

teamNickname = {alias.lower(): team for team, nicknames in TEAM.items() for alias in nicknames}

sentimentAnalyser = SentimentIntensityAnalyzer()

def cleanEmoji(text):
    return emoji.demojize(text).replace("::", " ").replace(":", "").replace("_", " ")

def cleanText(text):
    url = 'http://localhost:8888/text-clean'
    try:
        response = requests.post(url, json={"text": text})
        return response.json().get("cleanedText", text)
    except Exception as e:
        print(f"Text clean service error: {e}")
        return text

def teamMentioned(text):
    return list({team for alias, team in teamNickname.items() if alias in text.lower()})

def sentimentPerTeam(text, upvoteScore=1):
    sentences = sent_tokenize(text)
    teamSentiment = {team: [] for team in TEAM}
    for sentence in sentences:
        sentiment = sentimentAnalyser.polarity_scores(sentence)['compound']
        for team, nicknames in TEAM.items():
            if any(nickname in sentence.lower() for nickname in nicknames):
                teamSentiment[team].append(sentiment * abs(upvoteScore))
    resultSentiment = {}
    for team, sentiments in teamSentiment.items():
        if sentiments:
            resultSentiment[team] = round(sum(sentiments) / len(sentiments), 3)
    return resultSentiment

def harvest_afl_sentiment(keyword: str, limit: int = 1000):
    client = Client()
    client.login(os.getenv("BLUESKY_CLIENT_ID"), os.getenv("BLUESKY_CLIENT_PASSWORD"))

    posts = []
    cursor = None

    print(f"Harvesting posts for {keyword}...")

    while len(posts) < limit:
        harvest_limit = min(100, limit - len(posts))
        try:
            response = client.app.bsky.feed.search_posts(
                params=models.AppBskyFeedSearchPosts.Params(q=keyword, limit=harvest_limit, cursor=cursor)
            )
            if not response.posts:
                break
            for post in response.posts:
                try:
                    raw_text = post.record.text
                    text = cleanText(cleanEmoji(raw_text))
                    teams = teamMentioned(text)
                    upvote = getattr(post, 'likeCount', 1)
                    if teams:
                        sentiments = sentimentPerTeam(text, upvote)
                        for team, sentiment in sentiments.items():
                            posts.append({
                                '_index': 'afl-sentiment',
                                '_id': f"{post.uri.split('/')[-1]}_{team}_comment",
                                'platform': 'Bluesky',
                                'type': 'comment',
                                'team': team,
                                'sentiment': sentiment,
                                'text': text,
                                'upvote': upvote,
                                'createdOn': post.indexed_at,
                                'url': f"https://bsky.app/profile/{post.author.handle}/post/{post.uri.split('/')[-1]}",
                            })
                    else:
                        sentiment = sentimentAnalyser.polarity_scores(text)['compound'] * abs(upvote)
                        posts.append({
                            '_index': 'afl-sentiment',
                            '_id': f"{post.uri.split('/')[-1]}_{keyword}_comment",
                            'platform': 'Bluesky',
                            'type': 'comment',
                            'team': keyword,
                            'sentiment': round(sentiment, 3),
                            'text': text,
                            'upvote': upvote,
                            'createdOn': post.indexed_at,
                            'url': f"https://bsky.app/profile/{post.author.handle}/post/{post.uri.split('/')[-1]}",
                        })
                except Exception as e:
                    print(f"⚠️ Skipped post due to error: {e}")
            cursor = response.cursor
            if not cursor:
                break
        except Exception as e:
            print(f"❌ Error during harvest: {e}")
            break
        time.sleep(2)

    print(f"✅ Results for {keyword}: {len(posts)} posts harvested")
    return posts
