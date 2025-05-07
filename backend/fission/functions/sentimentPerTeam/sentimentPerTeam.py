import json
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from flask import request
# import nltk
# nltk.data.path.append("nltk_data")
# nltk.download('punkt')
# from nltk.tokenize import sent_tokenize
# add team in future if more team join ALF

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

sentimentAnalyser = SentimentIntensityAnalyzer()

def main():
#     """
#     Get total weighted sentiment per team , if team is not mentioned in posts then assumed its related to subredit team
#     """
    payload = request.json
    text = payload["text"]
    upvoteScore = payload.get("upvote",1)
    postTeams = payload["postTeams"]
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    teamSentiment = {team: [] for team in postTeams}
#     if not request.is_json:
#         return json.dumps({"error": "Invalid JSON"}), 400
    for sentence in sentences:
        sentiment = sentimentAnalyser.polarity_scores(sentence)['compound']
        teams = set()
        for team in postTeams:
            for teamName in TEAM[team]:
                if teamName in sentence.lower():
                    teams.add(team)
                    print([sentence,sentiment,team])

        if teams:
            weightSentiment = (sentiment * abs(upvoteScore)) / len(teams)
            for team in teams:
                teamSentiment[team].append(weightSentiment)
    resultSentiment = {}
    for team,sentiments in teamSentiment.items():
        if sentiments:
            resultSentiment[team] = round(sum(sentiments), 3) 
            
    return json.dumps(resultSentiment) 
