import requests
import time 
from elasticsearch8 import Elasticsearch, exceptions,ApiError 
from datetime import datetime
import json
from flask import current_app 

HEADERS = {
    "User-Agent": "AFL Bot - sentiment@bot.com"
}

def fetchGames(year=2025):
    url = f"https://api.squiggle.com.au/?q=games;year={year}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()["games"]
    else:    
        return "Fail"
     

def fetchLadder(year=2024, roundNumber=1):
    """
    Fetch ladder data only if it's from offical source=1
    """
    url = f"https://api.squiggle.com.au/?q=ladder;year={year};round={roundNumber};source=1"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()["ladder"]
    else:    
        return "Fail" 
def accuracy(goals, behinds):
    if goals is not None and behinds is not None and (goals + behinds) > 0:
        return round(goals / (goals + behinds), 4)
    return None


def addElastic(docID,indexText,doc):
    """
    Send data to fission function addelastic to store into elastic
    """
    current_app.logger.info(f'=== scoreHarvester: Adding Post {docID} ===')
    url='http://router.fission/addelastic'
    payload = {"indexDocument":indexText,"docID":docID,"doc":doc}  
    try:
        response = requests.post(url, json=payload, timeout=5) 
        current_app.logger.info(f'=== scoreHarvester AddElastic response: Exception in addElastic POST: {response.status_code} {response.text} ===') 
    except Exception as e:
        current_app.logger.info(f'=== scoreHarvester: Exception in addElastic POST: {str(e)} ===') 
     
    return "ok"

def checkPost(docID,indexDoc):
    """
    Check post ID see if exist in elastic index
    """
    current_app.logger.info(f'=== scoreHarvester: Checking Post {docID} ===')
    url='http://router.fission/checkelastic'
    payload = {
            "indexDocument": indexDoc,
            "docID": docID, 
        }
    res = requests.post(url,json=payload)
    return res.json()["found"]

def scoreHarvest(year=2024):
    """
    h stand for home , a stand for away 
    
    Handles:
    - squiggle data
    - JSON payload serialization 
    - store scores into elastic

    Returns:
        'OK' with HTTP 200 on successful enqueue 
    """
    current_app.logger.info(f'=== scoreHarvester: Scraping squiggle data ===')
    games = fetchGames(year)
    rounds = sorted(set(game["round"] for game in games if game["complete"] == 100))  

    for roundNumber in rounds:
        ladder = fetchLadder(year, roundNumber)
        ladderMap = {team["team"]: team["rank"] for team in ladder}
        if ladderMap == {}:
            continue     
        for game in games:
            if game["round"] == roundNumber:  
                if game["winner"] == None:
                    result = "Draw"
                elif game["hteam"].lower() == game["winner"].lower():
                    result = "Winner" 
                else:
                    result = "Loser" 
                homeDoc = {
                        "team": game["hteam"],
                        "opponent": game["ateam"],
                        "round": roundNumber,
                        "gameDate": game["localtime"].split(" ")[0],
                        "year": year,
                        "date": game["date"],
                        "venue": game["venue"],
                        "is_home": True,
                        "score": game["hscore"],
                        "goals": game["hgoals"],
                        "behinds": game["hbehinds"],
                        "accuracy": accuracy(game["hgoals"], game["hbehinds"]),
                        "result": result,
                        "margin": game["hscore"] - game["ascore"],
                        "roundname": game["roundname"],
                        "ladderRank":ladderMap[game["hteam"]],
                        "completed": True
                    }
                awayDoc = {
                        "team": game["ateam"],
                        "opponent": game["hteam"],
                        "round": roundNumber,
                        "gameDate": game["localtime"].split(" ")[0],
                        "year": year,
                        "date": game["date"],
                        "venue": game["venue"],
                        "is_home": False,
                        "score": game["ascore"],
                        "goals": game["agoals"],
                        "behinds": game["abehinds"],
                        "accuracy": accuracy(game["agoals"], game["abehinds"]),
                        "result": result,
                        "margin": game["ascore"] - game["hscore"],
                        "roundname": game["roundname"],
                        "completed": True
                    } 
                
                addElastic(f"home_{game['hteam']}_{roundNumber}","afl-scores",homeDoc)
                addElastic(f"away_{game['ateam']}_{roundNumber}","afl-scores",awayDoc) 
        time.sleep(1)  
    return "ok"

        
    
def main():
    """
    
    Handles: 
    - Calls scoreHarves for year 2024 until current year

    Returns:
        'OK' with HTTP 200 on successful enqueue

    Raises: 
        ApiError: These errors are triggered from an HTTP response is not 200:
    """
    try:
        for year in range(2024,datetime.now().year + 1):
            scoreHarvest(year) 
        current_app.logger.info(f'=== scoreHarvester: Scrape completed ===')
        return "ok",200
    except ApiError as e:
        return json.dumps({"error": str(e)}), 500
