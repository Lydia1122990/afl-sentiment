from flask import Flask, request, jsonify
import emoji
import json

app = Flask(__name__)

def clean_text_logic(text):
    invalidStr = {
        "::": " ",
        ":": "",
        "_": " ",
        "\n": "",
        "\u2019": "",
        "\u00a0": " ",
        "\u2026": "...",
        '"': ""
    }
    cleaned = emoji.demojize(text)
    for old, new in invalidStr.items():
        cleaned = cleaned.replace(old, new)
    return cleaned.strip()

@app.route("/text-clean", methods=["POST"])
def text_clean():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' in request"}), 400
    cleaned = clean_text_logic(data["text"])
    return jsonify({"cleanedText": cleaned})

if __name__ == "__main__":
    app.run(host="localhost", port=8888)

