from atproto import Client, models
import os
from dotenv import load_dotenv
import time

def harvest_afl_posts(keyword: str, limit: int = 1000):
    load_dotenv()
    client = Client()
    client.login(os.getenv("BLUESKY_CLIENT_ID"), os.getenv("BLUESKY_CLIENT_PASSWORD"))

    posts = []
    cursor = None

    while len(posts) < limit:
        remaining = limit - len(posts)
        harvest_limit = min(100, remaining)  

        try:
            response = client.app.bsky.feed.search_posts(
                params=models.AppBskyFeedSearchPosts.Params(
                    q=keyword,
                    limit=harvest_limit,
                    cursor=cursor
                )
            )
        except Exception as e:
            print(f"❌ fail to harvest（{keyword}）: {e}")
            break


        if not response.posts:
            break  

        for post in response.posts:
            try:
                posts.append({
                    'author': post.author.handle,
                    'text': post.record.text,
                    'post_time': post.indexed_at,
                    'url': f"https://bsky.app/profile/{post.author.handle}/post/{post.uri.split('/')[-1]}",
                    'uri': post.uri,
                })
            except Exception as e:
                print(f"⚠️ skip one post for（{keyword}）: {e}")
                continue


        cursor = response.cursor
        if not cursor:
            break  

        time.sleep(2)  

    return posts

