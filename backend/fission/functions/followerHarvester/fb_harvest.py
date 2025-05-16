from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from elasticsearch import Elasticsearch
from datetime import datetime
import os
import time
import re

# 从 Fission Secret 挂载的路径读取 ES 用户名密码
def get_es_auth():
    try:
        with open("/secrets/default/elastic-secret/ES_USERNAME") as f:
            username = f.read().strip()
        with open("/secrets/default/elastic-secret/ES_PASSWORD") as f:
            password = f.read().strip()
        return username, password
    except Exception as e:
        print(f"Error loading ES credentials: {e}")
        return "elastic", ""

# 初始化 ES 客户端
def connect_elasticsearch():
    es_username, es_password = get_es_auth()
    es_host = "https://elasticsearch-master.elastic.svc.cluster.local:9200"

    print(f"Connecting to Elasticsearch at {es_host}")
    try:
        es = Elasticsearch(
            hosts=[es_host],
            basic_auth=(es_username, es_password),
            verify_certs=False,
            ssl_show_warn=False
        )
        info = es.info()
        print(f"✅ Connected to Elasticsearch {info['version']['number']}")
        return es
    except Exception as e:
        print(f"❌ Error connecting to Elasticsearch: {e}")
        raise

# 粉丝抓取主逻辑
def main():
    INDEX_NAME = "afl_fb_fans-2"
    retrieval_time = datetime.now().isoformat().replace(":", "-")

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

    # 设置 Selenium 浏览器
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    es = connect_elasticsearch()

    try:
        for team, url in afl_teams_fb.items():
            print(f"➡ Fetching fans count for {team}")
            try:
                driver.get(url)
                time.sleep(4)
                page = driver.page_source
                match = re.search(r'([\d.,KkMm]+)\s+followers', page, re.IGNORECASE)
                followers = match.group(1) if match else "N/A"

                doc_id = f"{team}_{retrieval_time}"
                doc = {
                    "team": team,
                    "followers": followers,
                    "retrieved_at": retrieval_time
                }

                es.index(index=INDEX_NAME, id=doc_id, document=doc)
                print(f"✅ Saved {team}: {followers}")

            except Exception as e:
                print(f"⚠️ Failed to fetch {team}: {e}")

    finally:
        driver.quit()

    print("🏁 Facebook fans harvesting complete!")

if __name__ == "__main__":
    main()
