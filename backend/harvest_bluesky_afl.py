from atproto import Client, models
import os
from dotenv import load_dotenv
import time
from sentiment_bluesky import get_afl_teams  

def harvest_afl_posts(keyword: str, limit: int = 1000):
    load_dotenv()
    client = Client()
    client.login(os.getenv("BLUESKY_CLIENT_ID"), os.getenv("BLUESKY_CLIENT_PASSWORD"))

    posts = []
    cursor = None

    print(f"Harvesting posts for {keyword}...")

    while len(posts) < limit:
        remaining = limit - len(posts)
        harvest_limit = min(100, remaining)  

        try:
            # If we get validation errors, we don't want to completely fail the harvest
            # We'll just try a smaller batch size
            current_limit = harvest_limit
            
            while True:
                try:
                    response = client.app.bsky.feed.search_posts(
                        params=models.AppBskyFeedSearchPosts.Params(
                            q=keyword,
                            limit=current_limit,
                            cursor=cursor
                        )
                    )
                    # If we get here, the request succeeded
                    break
                except Exception as api_error:
                    # If the error is about aspectRatio validation
                    if "aspectRatio" in str(api_error):
                        # Try with a smaller batch size to avoid the problematic posts
                        current_limit = max(1, current_limit // 2)
                        print(f"Reducing batch size to {current_limit} to avoid validation errors")
                        if current_limit <= 5:  # If we're down to very small batches
                            # Just give up on this keyword and move on
                            raise  # Re-raise the exception to be caught by outer try/except
                    else:
                        # Some other API error
                        raise
            
            if not response.posts:
                break  

            for post in response.posts:
                try:
                    # Process each post, skipping any that cause errors
                    posts.append({
                        'author': post.author.handle,
                        'text': post.record.text,
                        'post_time': post.indexed_at,
                        'url': f"https://bsky.app/profile/{post.author.handle}/post/{post.uri.split('/')[-1]}",
                        'uri': post.uri,
                    })
                except Exception as e:
                    print(f"⚠️ skip one post for ({keyword}): {e}")
                    continue

            # Update cursor for next page
            cursor = response.cursor
            if not cursor:
                break
                
        except Exception as e:
            print(f"❌ fail to harvest ({keyword}): {e}")
            # Return whatever posts we've gathered so far
            break

        time.sleep(2)  # Be nice to the API

    print(f"Results for {keyword}: {len(posts)} posts harvested")
    return posts


all_results = {}
teams = get_afl_teams()
for team in teams:
    try:
        team_posts = harvest_afl_posts(team)
        all_results[team] = team_posts
    except:
        all_results[team] = []