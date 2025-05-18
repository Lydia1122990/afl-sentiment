import emoji
import json 
from flask import request,current_app

def main():
    """
    Process text and remove unnecessary text.
    return: cleaned text
    """
    try:
        current_app.logger.info(f'=== cleantext: Intitalise ===')
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
 
        return  json.dumps({"cleanedText": cleaned})
    except Exception as e:
        current_app.logger.info(f'=== cleantext: failed {e} ===')
        return "=== Clean text failed ==="