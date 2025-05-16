from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
from datetime import datetime
import os
import time
import re

# 载入环境变量
load_dotenv()

# Elastic连接
es_username = os.getenv("ES_USERNAME", "elastic")
es_password = os.getenv("ES_PASSWORD", "")
es_host = "https://localhost:9200"

print(f"Connecting to Elasticsearch at {es_host}")

try:
    es = Elasticsearch(
        hosts=[es_host],
        basic_auth=(es_username, es_password),
        verify_certs=False,
        ssl_show_warn=False
    )
    info = es.info()
    print(f"Successfully connected to Elasticsearch {info['version']['number']}")
except Exception as e:
    print(f"Error connecting to Elasticsearch: {e}")
    import traceback
    traceback.print_exc()
    import sys
    sys.exit(1)

# 常量
INDEX_NAME = "afl_fb_fans-3"

# Facebook Team列表
afl_teams_fb = {
    "adelaidecrows": "https://www.facebook.com/adelaidecrows",
    "brisbanelions": "https://www.facebook.com/brisbanelions",
    "carltonfc": "https://www.facebook.com/OfficialCarltonFC",
    "collingwoodfc": "https://www.facebook.com/CollingwoodFC",
    "essendonfc": "https://www.facebook.com/EssendonFC",
    "fremantle": "https://www.facebook.com/freodockers",
    "geelongcats": "https://www.facebook.com/geelongcats",
    "goldcoastsuns": "https://www.facebook.com/GoldCoastFC",
    "gws": "https://www.facebook.com/GWSGIANTS",
    "hawthorn": "https://www.facebook.com/HawthornFC",
    "melbourne": "https://www.facebook.com/melbournefc",
    "northmelbourne": "https://www.facebook.com/NMFCOfficial",
    "portadelaide": "https://www.facebook.com/PortAdelaideFC",
    "richmond": "https://www.facebook.com/richmondfc",
    "stkilda": "https://www.facebook.com/stkfc",
    "sydneyswans": "https://www.facebook.com/sydneyswans",
    "westcoasteagles": "https://www.facebook.com/WCEofficial",
    "westernbulldogs": "https://www.facebook.com/westernbulldogs"
}

def main():
    retrieval_time = datetime.now().isoformat().replace(":", "-")

    # 配置Selenium
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    try:
        for team, url in afl_teams_fb.items():
            print(f"Fetching fans count for {team}...")
            driver.get(url)
            time.sleep(5)

            page = driver.page_source
            match = re.search(r'([\d.,KkMm]+)\s+followers', page, re.IGNORECASE)
            followers = match.group(1) if match else "N/A"

            doc_id = f"{team}_{retrieval_time}"  # 每次不同，保留历史
            doc = {
                "team": team,
                "followers": followers,
                "retrieved_at": retrieval_time
            }

            try:
                # 用index而不是create，直接新插入一条
                es.index(index=INDEX_NAME, id=doc_id, document=doc)
                print(f"Successfully saved {team}")

            except Exception as e:
                print(f"Error saving {team}: {e}")

    finally:
        driver.quit()

    print("✅ Facebook fans harvesting complete!")

if __name__ == "__main__":
    main()
