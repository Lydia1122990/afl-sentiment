from bs4 import BeautifulSoup
import time
import requests
import hashlib
import random
import traceback

# Australian city abbreviations and full names, for searching
city_name = ["melb", "melbourne", "syd", "sydney", "bne", "brisbane", "adl", "adelaide", "perth",
            "cbr", "canberra", "hobart", "darwin","hba", "drw", "per"]

# Mapping from city abbreviation or lowercase to standardized full names
city_name_map = {
    "melb": "melbourne",
    "syd": "sydney",
    "bne": "brisbane",
    "adl": "adelaide",
    "cbr": "canberra",
    "per": "perth",
    "hba": "hobart",
    "drw": "darwin",
    "melbourne": "melbourne",
    "sydney": "sydney",
    "brisbane": "brisbane",
    "adelaide": "adelaide",
    "perth": "perth",
    "canberra": "canberra",
    "hobart": "hobart",
    "darwin": "darwin"
}


# Strong keywords: You must hit at least 1 keyword to qualify as a post to be harvested
strong_keywords = [
    "train", "tram", "bus", "metro", "subway", "shuttle", "skybus", "light rail",
    "myki", "opal", "gocard", "ptv", "yarratrams", "vline",
    "translink", "metrocard", "myway", "vicroads", "transportnsw", "rms"
]

# Weak keywords: can help further confirm whether it is a traffic topic, and must appear together with strong keywords
weak_keywords = [
    "fare", "ticket", "inspector", "fined", "caught", "forgot", "tap",
    "delay", "cancelled", "shutdown", "no service", "replacement", "trackwork",
    "maintenance", "signal", "fault", "engineering", "driver", "shortage",
    "diversion", "congestion", "accident", "commute", "commuting",
    "crowded", "overcrowded", "public transport", "toll", "car crash"
]

# Mistakenly triggered keywords: Once a post contains these keywords, it will be ignored (avoid matching MMA, scientific research, sports)
banned_keywords = [
    "road", "race", "weekend", "ranked", "rank", "run", "process", "line"
]

# Total set of all keywords
transport_keywords = strong_keywords + weak_keywords


# Function to remove HTML tags and convert to lowercase
def text_extract(content):
    return BeautifulSoup(content, "html.parser").get_text().lower()

def match_topic(text):
    """
    Determine whether the text is a traffic-related topic:
    - No accidentally touched keywords
    - At least 1 strong keyword
    - The total number of strong + weak keywords ≥ 2
    """
    text = text.lower()

    # If it contains any misleading keywords, just ignore this post
    if any(keyword in text for keyword in banned_keywords):
        return False

    strong_count = sum(1 for keyword in strong_keywords if keyword in text)
    weak_count = sum(1 for keyword in weak_keywords if keyword in text)

    total_count = strong_count + weak_count

    return total_count >= 2 and strong_count >= 1


# Function used to determine whether the text contains a city name
def city_contain(text, city):
    return city.lower() in text.lower()

def posts_processing(post, city, sentiment_analyser):
    try:
        if "arxiv" in post["account"]["acct"]:
            return  # Ignore content from arXiv bot account

        content = text_extract(post.get("content", ""))
        if len(content) > 3000 or not match_topic(content) or not city_contain(content, city):
            return
        
        url = post.get("url")
        if (url, city) in harvested_url_city:
            return  # Skip duplicate fetches
        harvested_url_city.add((url, city))

        score = sentiment_analyser.polarity_scores(content)["compound"]

        # Map city to standardized full name
        standard_city = city_name_map.get(city.lower(), city)

        doc = {
            "platform": "Mastodon",
            "city": standard_city,
            "author": post["account"]["acct"],
            "sentiment": score,
            "text": content,
            "createdOn": post["created_at"].isoformat(),
            "url": url,
        }

        post_json_all.append(doc)
        print(f"Harvested posts: {standard_city}  | {url}")

    except Exception as e:
        print(f"Error processing: {e}")
        traceback.print_exc()

# This function is used to search for posts from Mastodon based on keywords, supporting page turning and retrying upon failure
def get_post(query, max_post, mastodon, max_attempt=2):
    post_list = []
    page_turn_mark = None
    attempt = 0

    while len(post_list) < max_post:
        try:
            results = mastodon.search_v2(query, result_type="statuses", max_id=page_turn_mark)
            post = results["statuses"]
            if not post:
                break
            post_list.extend(post)
            page_turn_mark = post[-1]["id"]
            attempt = 0
        except Exception as e:
            print(f"Error for '{query}': {e}")
            traceback.print_exc()
            attempt += 1
            if attempt >= max_attempt:
                print(f"Failed after {max_attempt} attempts. Skipping query.")
                break
            else:
                print(f"Retrying ({attempt}/{max_attempt})...")
                time.sleep(3)

    return post_list[:max_post]


def main():
    """
    Main execution function:
    1. Load key
    2. Get data from Mastodon
    3. Filter posts and extract sentiment
    4. Upload to Elasticsearch
    """
    try:
        from mastodon import Mastodon
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        import time

        time.sleep(15) # Give services/dependencies time to prepare

        with open("/secrets/default/elastic-secret-mastodon/MASTODON_ACCESS_TOKEN", 'r') as f:
            mastodon_token = f.read().strip()

        # Initialize the Mastodon client and sentiment analyzer
        mastodon = Mastodon(access_token=mastodon_token, api_base_url="https://mastodon.social", request_timeout=30)
        sentiment_analyser = SentimentIntensityAnalyzer()

        global post_json_all, harvested_url_city
        post_json_all = []
        harvested_url_city = set()

        # Randomly select cities and keywords
        random.shuffle(city_name)
        random.shuffle(transport_keywords)

        city = city_name[0]
        keyword = transport_keywords[0]
        max_post = 50  

        print(f"Selected city: {city}")
        print(f"Selected keyword: {keyword}")

        query = f"{city} {keyword}"
        print(f"Query: {query}")

        # Fetch posts
        posts = get_post(query, max_post, mastodon)

        time.sleep(1.5)  # Prevent current limiting from being triggered
        
        # Process and filter valid content
        for post in posts:
            posts_processing(post, city, sentiment_analyser)


        # Fission uploader endpoint
        uploader_url = "http://router.fission/addelastic"

        for doc in post_json_all:
            try:
                # Using URL as unique ID
                url = doc.get("url", "")
                doc_id = hashlib.md5(url.encode()).hexdigest() if url else None

                payload = {
                    "docID": doc_id,
                    "indexDocument": "mastodon_v2", 
                    "doc": doc
                }

                res = requests.post(uploader_url, json=payload, timeout=10)
                if res.status_code not in [200, 201]:
                    print(f"Upload Failed [{res.status_code}]")
                else:
                    print("Upload Success!")
            except Exception as e:
                print(f"Exception while uploading to elastic uploader: {e}")

        return {"statusCode": 200, "message": "Harvesting complete"}



    except Exception as e:
        return {"statusCode": 500, "body": f"Error: {e}"}
