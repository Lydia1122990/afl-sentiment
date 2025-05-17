from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from elasticsearch8 import Elasticsearch, exceptions
from datetime import datetime
import os
import re
import time

INDEX_NAME = "afl_fb_fans-444"

def main():
    # === 读取 Secret ===
    try:
        with open("/secrets/default/elastic-secret/ES_USERNAME") as f:
            es_username = f.read().strip()

        with open("/secrets/default/elastic-secret/ES_PASSWORD") as f:
            es_password = f.read().strip()
    except Exception as e:
        print(f"Failed to read secrets: {e}")
        return "error"

    # === 连接 Elasticsearch ===
    try:
        es = Elasticsearch(
            hosts=["https://elasticsearch-master.elastic.svc.cluster.local:9200"],
            basic_auth=(es_username, es_password),
            verify_certs=False,
            ssl_show_warn=False
        )
        print("✅ Connected to Elasticsearch", flush=True)
    except Exception as e:
        print(f"Elasticsearch connection failed: {e}")
        return "error"

    # === Facebook Team 列表 ===
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

    # === Selenium 设置 ===
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    retrieval_time = datetime.now().isoformat().replace(":", "-")

    try:
        for team, url in afl_teams_fb.items():
            print(f"Fetching: {team}", flush=True)
            driver.get(url)
            time.sleep(5)  # 等待页面加载

            page = driver.page_source
            match = re.search(r'([\d.,KkMm]+)\s+followers', page, re.IGNORECASE)
            followers = match.group(1) if match else "N/A"

            doc_id = f"{team}_{retrieval_time}"
            doc = {
                "team": team,
                "followers": followers,
                "retrieved_at": retrieval_time
            }

            try:
                es.create(index=INDEX_NAME, id=doc_id, document=doc)
                print(f"✅ Saved {team}", flush=True)
            except exceptions.ConflictError:
                print(f"⚠️ Document for {team} already exists", flush=True)
            except Exception as e:
                print(f"❌ Error saving {team}: {e}", flush=True)

    finally:
        driver.quit()

    return "ok"
