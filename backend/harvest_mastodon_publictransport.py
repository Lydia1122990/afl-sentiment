from mastodon import Mastodon
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import nltk
import time
import os
import json
import re
import traceback

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

load_dotenv() #Load environment variables from .env into python
sentiment_analyser = SentimentIntensityAnalyzer() #Initialize a sentiment analyzer object

# Initialize a Mastodon client object to connect to the Mastodon social platform API
mastodon = Mastodon(
    access_token=os.getenv("MASTODON_ACCESS_TOKEN"),
    api_base_url="https://mastodon.social"
)

# Aus City Name
city_name = ["melb", "melbourne", "syd", "sydney", "bne", "brisbane", "adl", "adelaide", "perth",
    "cbr", "canberra", "hobart", "darwin"]

# A keyword list specifically for public transportation related terms.
transport_keywords = [
    "train", "trains", "tram", "trams", "bus", "buses", "metro", "subway", "shuttle", "light rail", "skybus",

    "ptv", "myki", "vline", "yarratrams", "metro trains",

    "opal",          # Sydney
    "translink",     # Brisbane
    "adelaidemetro", # Adelaide
    "act transport", # Canberra
    "perth transport",  # Perth 
    "hobart bus",    # Hobart 
    "darwinbus",     # Darwin

    "train fare", "tram fare", "bus fare", "metro fare", "vline fare", "light rail fare",
    "train ticket", "tram ticket", "bus ticket", "metro ticket", "vline ticket",

    "train delay", "tram delay", "bus delay", "vline delay",
    "train cancelled", "tram cancelled", "bus cancelled",
    "train shutdown", "tram shutdown", "rail shutdown",
    "train maintenance", "tram maintenance", "track maintenance", "signal fault",

    "train replacement", "tram replacement", "bus replacement", "replacement bus",
    "train trackwork", "tram trackwork", "bus trackwork",
    "train service change", "tram service change", "bus service change",
    "train no service", "tram no service", "bus no service",
    "train diversion", "tram diversion", "bus diversion",
    "train engineering works", "tram engineering works", "bus engineering works",
    "train weekend closure", "tram weekend closure", "bus weekend closure",
    "train driver shortage", "tram driver shortage", "bus driver shortage"

    "crowded train", "crowded tram", "overcrowded bus", "late train", "on time train", "train overcrowding"

    "fare evasion", "ticket evasion", "dodging fare", "fare dodger",
    "fare dodging", "evading fare", "jumping fare", "ride without ticket",
    "got caught without myki", "fare fine",
    "fined for no ticket", "didn't tap on", "forgot to tap", 
    "inspection", "ticket inspector", "ticket check", "fare compliance"

    # Melbourne
    "no myki", "myki fine", "forgot myki", "didn't tap myki",
    "myki evasion", "caught without myki"

    # Sydney
    "no opal", "opal fine", "forgot opal", "didn't tap opal",
    "opal evasion", "caught without opal"
    # Brisbane
    "no gocard", "go card fine", "forgot go card", "didn't tap go card",
    "translink fine", "caught without gocard"
    # Adelaide
    "no metrocard", "metrocard fine", "adelaide metro fine", "forgot metrocard"
    # Canberra
    "no myway", "myway fine", "didn't tap myway"

]



# Mastodon posts are in HTML format by default, so we define a function to extract HTML content.
def text_extract(content):
    return BeautifulSoup(content, "html.parser").get_text().lower()

# A function is used to determine whether a post contains keywords related to traffic.
def match_topic(text):
    # Lowercase 
    text = text.lower()
    # Remove punctuation   
    text = re.sub(r'[^\w\s]', '', text)
    # Tokenisation
    tokens = word_tokenize(text)
    # Remove stopwords   
    stop_words = set(stopwords.words('english'))
    tokens = [t for t in tokens if t not in stop_words]
    # Lemmatisation
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(t) for t in tokens]
    
    return any(t in transport_keywords for t in tokens)

# Determine whether a city is mentioned in the text
def city_contain(text, city):
    return city.lower() in text.lower()

# Process each fetched Mastodon post
def posts_processing(post, city):
    try:
        content = text_extract(post.get("content", ""))
        # If the posts are too long, they may be off topic, so you need to ignore them.
        # Use the function defined above to filter posts in a certain city
        if len(content) > 700  or not match_topic(content) or not city_contain(content, city):
            return
        
        url = post.get("url")
        # If this post about a city has already been processed, it will be skipped.
        # Otherwise, it will be added to the harvested set, indicating that the information about this city in this post has been extracted.
        if (url, city) in harvested_url_city:
            return
        harvested_url_city.add((url, city))

        # Get the comprehensive sentiment score of a piece of text
        score = sentiment_analyser.polarity_scores(content)["compound"]
        
        # Encapsulate the post information into a JSON-friendly Python dictionary object
        doc = {
            "platform": "Mastodon",
            "city": city,
            "author": post["account"]["acct"],
            "sentiment": score,
            "text": content,
            "createdOn": post["created_at"],
            "url": url,
        }
        # Add this post to a global list. This list will be saved in a JSON file.
        post_json_all.append(doc)
        # View processing progress
        print(f"Harvested posts: {city}  | {url}")

    except Exception as e:
        print(f"Error processing: {e}")
        traceback.print_exc()

# A function that sends a keyword search request to the Mastodon API and fetches the resulting posts in pages
def get_post(query, max_post):
    # Create a list to store all the captured posts
    post_list = []
    # Since Mastodon has a maximum of 20 posts per page, we need to mark the location where we will start crawling posts next time.
    page_turn_mark = None

    # When the number of posts that have been crawled is less than the maximum number allowed to crawl, execute the while loop
    while len(post_list) < max_post:
        try:
            # Makes a search request to Mastodon for posts matching query, and specifies page_turn_mark to control "pagination".
            # Statuses indicates that it only checks "post content"
            results = mastodon.search_v2(query, result_type="statuses", max_id=page_turn_mark)
            # Extract a list of all posts returned by this page.
            post = results["statuses"]

            # If the post content is empty, it means that all posts have been harvested and the loop ends.
            if not post:
                break

            # Add a whole page of posts to the full post list
            post_list.extend(post)
            # Find the ID of the last post and use it as a pagination marker for the next page.
            page_turn_mark = post[-1]["id"]
            # Avoid triggering the rate limiting mechanism of the Mastodon API.
            time.sleep(1.2) 
        except Exception as e:
            print(f" Error request '{query}': {e}")
            break

    # Returns all posts in post_list.
    return post_list[:max_post]


post_json_all = []
harvested_url_city = set()
max_post = 5

if __name__ == "__main__":
    
    # The outer loop iterates over all cities
    for city in city_name:
        print(f"Searching posts related to: {city}")
        # The inner loop traverses all traffic-related keywords.
        for keyword in transport_keywords:
            # Combine city and traffic keywords to generate query keywords.
            query = f"{city} {keyword}"
            print(f"Query: {query}")
            # Call the above function to fetch related posts.
            posts = get_post(query, max_post)
            # Process each captured post.
            for post in posts:
                posts_processing(post, city)
    # Write the processed posts to a JSON file.
    with open("mastodon_transport_sentiment.json", "w", encoding="utf-8") as f:
        json.dump(post_json_all, f, indent=2, ensure_ascii=False, default=str)

    print(f"Post harvesting completed. A total of {len(post_json_all)} posts were harvested.")