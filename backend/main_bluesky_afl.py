from sentiment_bluesky import harvest_afl_sentiment, get_afl_teams
from es_utils import save_to_elasticsearch

import os
import time
import pandas as pd
import json

# 文件保存路径 test
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

# 主执行逻辑
seen_uris = load_seen_uris()
all_posts = []
new_uris = set()

teams = get_afl_teams()
for team in teams:
    print(f"Harvesting posts for {team}...")
    posts = harvest_afl_sentiment(team, limit=100)

    time.sleep(5)
    team_posts = []

    for post in posts:
        if post["url"] in seen_uris:
            continue
        new_uris.add(post["url"])

        # Remove Elasticsearch metadata fields
        post_cleaned = {k: v for k, v in post.items() if k not in ['_index', '_id']}
        doc_id = f"{team}_{len(team_posts)}"

        all_posts.append(post_cleaned)
        team_posts.append((doc_id, post_cleaned))

        # Save to Elasticsearch
        save_to_elasticsearch([post_cleaned], index_name="afl_bluesky_sentiment", doc_id=doc_id)

# 更新 seen_uris 文件
save_seen_uris(new_uris)

# 保存至 Elasticsearch (bulk)
save_to_elasticsearch(all_posts, index_name="afl_bluesky_sentiment")

# 保存为本地 CSV / JSON
os.makedirs("results", exist_ok=True)

# Save as CSV
df = pd.DataFrame(all_posts)
df.to_csv("results/afl_posts.csv", index=False)

# Save as JSON
with open("results/afl_posts.json", "w", encoding="utf-8") as f:
    json.dump(all_posts, f, ensure_ascii=False, indent=2)

print("✅ Harvest complete. Results saved to CSV, JSON, and Elasticsearch.")
