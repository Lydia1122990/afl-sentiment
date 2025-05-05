import os
import time
import emoji
from dotenv import load_dotenv
from atproto import Client, models
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from nltk.tokenize import sent_tokenize
import nltk
nltk.download('punkt_tab')

TEAM = {"adelaidefc":["adelaide crows","crows", "crows reserves", "whites", "white noise","kuwarna"],
        "brisbanelions":["brisbane lions","maroons", "gorillas", "lions"],
        "carltonblues":["carlton","blues","blue baggers","baggers","old navy blues"],
        "collingwoodfc":["collingwood","magpies","pies","woods","woodsmen"],
        "essendonfc":["essendon","bombers","dons","same olds"],
        "fremantlefc":["fremantle","dockers","freo","walyalup"], 
        "geelongcats":["geelong","cats"],
        "gcfc":["gold coast suns","suns","sunnies","coasters"],
        "gwsgiants":["gws giants","greater western sydney giants","giants","gws","orange team"],
        "hawktalk":["hawthorn","hawks"],
        "melbournefc":["melbourne","demons","dees","narrm","redlegs","fuchsias"],
        "northmelbournefc":["north melbourne","kangaroos","kangas","roos","north","shinboners"],
        "weareportadelaide":["port adelaide","power","port","cockledivers", "seaside men", "seasiders", "magentas", "portonians", "ports"],
        "richmondfc":["richmond","tigers", "tiges", "fighting fury"],
        "stkilda":["st kilda","saints","sainters"],
        "sydneyswans":["sydney swans","swans","swannies", "bloods"],
        "westcoasteagles":["west coast eagles","eagles"],
        "westernbulldogs":["western bulldogs","dogs", "doggies", "scraggers", "the scray", "footscray", "tricolours"],
        "tasmanianafl":["tasmania football club","devils", "tassie"]}
# map nickname to team name
teamNickname = {}
for team, nicknames in TEAM.items():
    for alias in nicknames:
        teamNickname[alias.lower()] = team



# Initialize sentiment analyzer
sentimentAnalyser = SentimentIntensityAnalyzer()

def cleanEmoji(text):
    """Convert emojis to text and remove formatting artifacts."""
    return emoji.demojize(text).replace("::", " ").replace(":", "").replace("_", " ")

def teamMentioned(text, teams=teamNickname):
    foundTeam = set()
    for nickname, team in teams.items():
        if nickname in text.lower():
            foundTeam.add(team)
    return list(foundTeam)

def sentimentPerTeam(text, upvoteScore=1, teams=TEAM):
    sentences = sent_tokenize(text)
    teamSentiment = {team: [] for team in TEAM}
    
    for sentence in sentences:
        score = sentimentAnalyser.polarity_scores(sentence)['compound']
        for team, nicknames in TEAM.items():
            if any(nickname in sentence.lower() for nickname in nicknames):
                teamSentiment[team].append(score * abs(upvoteScore)) 
                
    resultSentiment = {}
    for team, scores in teamSentiment.items():
        if scores:
            resultSentiment[team] = round(sum(scores) / len(scores), 3)
        elif any(nickname in text.lower() for nickname in TEAM[team]):
            score = sentimentAnalyser.polarity_scores(text)['compound']
            resultSentiment[team] = round(score * abs(upvoteScore), 3)
    return resultSentiment

def harvest_afl_sentiment(keyword: str, limit: int = 1000):
    load_dotenv()
    client = Client()
    client.login(os.getenv("BLUESKY_CLIENT_ID"), os.getenv("BLUESKY_CLIENT_PASSWORD"))

    posts = []
    cursor = None

    while len(posts) < limit:
        remaining = limit - len(posts)
        harvest_limit = min(100, remaining)

        try:
            response = client.app.bsky.feed.search_posts(
                params=models.AppBskyFeedSearchPosts.Params(
                    q=keyword,
                    limit=harvest_limit,
                    cursor=cursor
                )
            )

            if not response.posts:
                break

            for post in response.posts:
                try:
                    text = cleanEmoji(post.record.text)
                    teams = teamMentioned(text)
                    sentiment = sentimentPerTeam(text) if teams else {"general": sentimentAnalyser.polarity_scores(text)['compound']}
                    posts.append({
                        'keyword': keyword,
                        'author': post.author.handle,
                        'text': text,
                        'post_time': post.indexed_at,
                        'url': f"https://bsky.app/profile/{post.author.handle}/post/{post.uri.split('/')[-1]}",
                        'uri': post.uri,
                        'sentiment': sentiment
                    })
                except Exception as e:
                    print(f"⚠️ Skipped post due to error: {e}")
                    continue

            cursor = response.cursor
            if not cursor:
                break

        except Exception as e:
            print(f"❌ Error during harvest: {e}")
            break

        time.sleep(2)

    return posts
