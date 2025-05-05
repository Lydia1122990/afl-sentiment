import praw
from praw.models.listing.mixins import submission
from praw.reddit import Subreddit
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer 
from elasticsearch import Elasticsearch, exceptions
import os
from datetime import datetime
from dotenv import load_dotenv 
import nltk
nltk.download('punkt_tab')
import emoji
from nltk.tokenize import sent_tokenize


load_dotenv()
# reddit auth

sentimentAnalyser = SentimentIntensityAnalyzer()

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


def cleanEmoji(text):
    
    """
    Remove emoji and return text
    task: might need to edit vadot text to read emoji
    """ 
    return emoji.demojize(text).replace("::"," ").replace(":","").replace("_"," ")

def teamMentioned(text, teams=teamNickname):
    """
    Found team mentioned in the team
    """
    foundTeam = set()
    for nickname, team in teams.items():
        if nickname in text.lower():
            foundTeam.add(team)
    return list(foundTeam)

def sentimentPerTeam(text,upvoteScore=1, teams=TEAM):
    """
    Get total weighted sentiment per team , if team is not mentioned in posts then assumed its related to subredit team
    """
    sentences = sent_tokenize(text)
    teamSentiment = {team: [] for team in TEAM}
    
    for sentence in sentences:
        sentiment = sentimentAnalyser.polarity_scores(sentence)['compound']
        for team, nicknames in TEAM.items():
            teamFound = any(nickname in sentence.lower() for nickname in nicknames)
            if teamFound:
                
                teamSentiment[team].append(sentiment * abs(upvoteScore)) 
    resultSentiment = {}
    for team,sentiments in teamSentiment.items():
        if sentiments:
            resultSentiment[team] = round(sum(sentiments) / sum([abs(upvoteScore)] * len(sentiments)), 3)
        elif any(nickname in text.lower() for nickname in TEAM[team]):
                sentiments = sentimentAnalyser.polarity_scores(text)['compound']
                resultSentiment[team] = round(sentiments * abs(upvoteScore), 3)
    return resultSentiment 

def storeElastic(text,post,postType,sentiments, teamsBool):
    es_password = os.getenv("ES_PASSWORD")
    es_username = os.getenv("ES_USERNAME")
    es = Elasticsearch(
    hosts=["http://localhost:9200"],
    basic_auth=(es_username, es_password))
    try:
        if teamsBool:
            for team,sentiment in sentiments.items(): 
                doc = {"type": postType,
                       
                      "team": team,
                      "sentiment":sentiment,
                      "text": text,
                      "upvote":post.score,
                      "createdOn": datetime.fromtimestamp(post.created_utc).isoformat(),
                      "url":post.url,
                }
        else:
            doc = {"type": postType,
                       
                      "team": post.subreddit.display_name,
                      "sentiment":sentiments,
                      "text": text,
                      "upvote":post.score,
                      "createdOn": datetime.fromtimestamp(post.created_utc).isoformat(),
                      "url":post.url,
                }
        return "ok"
    #             es.create(index="afl-sentiment",id=f"{post.id}_{team}",document=doc)
    except exceptions.ConflictError:
        print("Document already exists, skipping...")
        return "ok"
        
 
def harvestSubreddit(redditTeam, postLimits=10):
    """
    Harvest post and its comments and get the sentiment value
    """ 
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent="python:reddit-harvester:v1.0 (by /u/Exact_Agency_3144)",
    )
    subreddit = reddit.subreddit(redditTeam)

    for post in subreddit.new(limit=postLimits): 
        text = cleanEmoji(post.title + " " + post.selftext) 
        postTeams = teamMentioned(text)
        
        if postTeams:
            sentiment = sentimentPerTeam(text,post.score, postTeams) 
            storeElastic(text,post,"post",sentiment,True)
        else: 
            sentiment =  sentimentAnalyser.polarity_scores(text)['compound'] 
            if(sentiment < 0.05):
                #set low impact sentiment to netural
                sentiment = 0.0
                # print(f"0.0: {text} {post.url}")
            storeElastic(text,post,"post",sentiment,False)
            
        post.comments.replace_more(limit=0) 

        for comment in post.comments.list():
            commentText = cleanEmoji(comment.body)
            # Skip if it's reply to another comment AND doesn't mention a team
            if comment.parent_id.startswith("t1_") and not teamMentioned(comment.body):
                continue
            mentioned = teamMentioned(commentText) 
            if mentioned:
                sentiment = sentimentPerTeam(commentText,comment.score)

                # print(f"comment {sentiment}")
                # print(f"Comment (Score: {comment.score}): {sentiment} \n-> {comment.body}\n")

harvestSubreddit("StKilda",postLimits=5)





