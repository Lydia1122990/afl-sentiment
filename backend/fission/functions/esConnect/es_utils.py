from elasticsearch import Elasticsearch
import traceback

# 从 Kubernetes Secret 中读取 Elasticsearch 凭证
try:
    with open("/secrets/default/elastic-secret/ES_USERNAME") as f:
        es_username = f.read().strip()

    with open("/secrets/default/elastic-secret/ES_PASSWORD") as f:
        es_password = f.read().strip()
except Exception as e:
    print(f"Error reading secret files: {e}")
    traceback.print_exc()
    import sys
    sys.exit(1)

# 测试连接信息
print(f"Connecting to Elasticsearch at https://elasticsearch-master.elastic.svc.cluster.local:9200")
print(f"Username: {es_username}")
print(f"Password length: {len(es_password) if es_password else 0}")

try:
    # For Elasticsearch 8.x
    es = Elasticsearch(
        hosts=["https://elasticsearch-master.elastic.svc.cluster.local:9200"],
        basic_auth=(es_username, es_password),
        verify_certs=False,
        ssl_show_warn=False
    )

    # Test connection
    info = es.info()
    print(f"Successfully connected to Elasticsearch {info['version']['number']}")

except Exception as e:
    print(f"Error connecting to Elasticsearch: {e}")
    traceback.print_exc()
    import sys
    sys.exit(1)

def save_to_elasticsearch(posts, index_name="afl_bluesky_sentiment", doc_id=None):
    try:
        # Check if index exists
        exists = es.indices.exists(index=index_name)
        print(f"Index {index_name} exists: {exists}")

        if not exists:
            # Create empty index
            es.indices.create(index=index_name)
            print(f"Index {index_name} created successfully")

    except Exception as e:
        print(f"Error checking/creating index: {e}")
        return False

    # Process posts
    success_count = 0
    error_count = 0

    for post in posts:
        try:
            this_id = doc_id or post.get("url", "").split("/")[-1]
            result = es.index(index=index_name, id=this_id, document=post)
            success_count += 1

            if success_count % 10 == 0:
                print(f"Successfully indexed {success_count} posts")

        except Exception as e:
            error_count += 1
            print(f"Error indexing post: {e}")

            if error_count == 1:
                print(f"First error details: {e}")
                traceback.print_exc()

    print(f"Indexing complete: {success_count} successes, {error_count} failures")
    return True