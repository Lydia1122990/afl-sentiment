import emoji
import json 
from flask import request

def main():
    # Parse JSON input
    data = request.get_json() 
    if "text" not in data:
        print("Missing text key in JSON data") 
        
    text = data["text"]
    cleaned = emoji.demojize(text).replace("::", " ").replace(":", "").replace("_", " ").replace("\n","")

    # Return cleaned text
    return  json.dumps({"cleanedText": cleaned})