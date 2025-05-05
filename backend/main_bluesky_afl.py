from harvest_bluesky_afl import harvest_afl_posts
from teams_bluesky_afl import AFL_TEAMS
import pandas as pd
import time
import json
import os

# seen_uris: avoid duplicate posts
SEEN_FILE = "seen_uris.txt"

def load_seen_uris(file_path=SEEN_FILE):
    if not os.path.exists(file_path):
        return set()
    with open(file_path, "r") as f:
        return set(line.strip() for line in f.readlines())

def save_seen_uris(uris, file_path=SEEN_FILE):
    with open(file_path, "a") as f:
        for uri in uris:
            f.write(uri + "\n")

# main
seen_uris = load_seen_uris()
all_posts = []
new_uris = set()

for team in AFL_TEAMS:
    print(f"Harvesting posts for {team}...")
    posts = harvest_afl_posts(team, limit=300)
    time.sleep(5)
    for post in posts:
        if post['uri'] in seen_uris:
            continue
        new_uris.add(post['uri'])
        post_data = {
            'keyword': team,
            'author': post['author'],
            'text': post['text'],
            'post_time': post['post_time'],
            'url': post['url'],
        }
        all_posts.append(post_data)


# save result
os.makedirs("results", exist_ok=True)

# save result as CSV
df = pd.DataFrame(all_posts)
df.to_csv("results/afl_posts.csv", index=False)

# save result as JSON
with open("results/afl_posts.json", "w", encoding="utf-8") as f:
    json.dump(all_posts, f, ensure_ascii=False, indent=2)

print("Results are saved as CSV file and JSON file")