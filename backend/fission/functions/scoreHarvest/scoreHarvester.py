import requests
import time 
from elasticsearch8 import Elasticsearch, exceptions,ApiError 
from datetime import datetime
import json

# fission package create --spec --name scoreharvester-pkg --source ./functions/scoreHarvest/scoreHarvester.py --source ./functions/scoreHarvest/requirements.txt --env python39 
# fission fn create --spec --name scoreharvester --pkg scoreharvester-pkg --env python39 --entrypoint scoreHarvester.main --secret elastic-secret
# fission route create --spec --name scoreharvester-route --function scoreharvester --url /scoreharvester --method POST --createingress
# fission timetrigger create --spec --name scoretimer --function scoreharvester --cron "0 1 0 * * MON"
# run every week on monday

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

def scoreHarvest(es,year=2024):
    """
    h stand for home , a stand for away
    """
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
                print(game) 
                print(ladderMap)   
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
                try:
                    es.create(index="afl-scores", id=f"home_{game['hteam']}_{roundNumber}", document=homeDoc) 
                    es.create(index="afl-scores", id=f"away_{game['ateam']}_{roundNumber}", document=awayDoc)
                except exceptions.ConflictError: 
                    print(f"Document home_{game['hteam']}_{roundNumber} already exists, skipping...")
                    continue
        time.sleep(1)  
    return "ok"

        
    
def main():
    try:
        with open("/secrets/default/elastic-secret/ES_USERNAME") as f:
            es_username = f.read().strip()

        with open("/secrets/default/elastic-secret/ES_PASSWORD") as f:
            es_password = f.read().strip()  
        es = Elasticsearch(hosts=["https://elasticsearch-master.elastic.svc.cluster.local:9200"], basic_auth=(es_username, es_password),verify_certs=False,ssl_show_warn=False) 
        for year in range(2024,datetime.now().year + 1):
            scoreHarvest(es,year) 
        return "ok",200
    except ApiError as e:
        return json.dumps({"error": str(e)}), 500
