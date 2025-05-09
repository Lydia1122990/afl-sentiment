import emoji
import json 
from flask import request

def main():
    # Parse JSON input
    data = request.get_json() 
    if "text" not in data:
        print("Missing text key in JSON data") 
        
    text = data["text"]
    invalidStr = {
    "::": " ",
    ":": "",
    "_": " ",
    "\n": "",
    "\u2019": "",
    '\u00a0': " ",
    '\u2026': "...",
    '"': ""
    }
    cleaned = emoji.demojize(text)
    for old, new in invalidStr.items():
        cleaned = cleaned.replace(old, new)

    # Return cleaned text
    return  json.dumps({"cleanedText": cleaned})