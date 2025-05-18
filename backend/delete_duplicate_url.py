from elasticsearch import Elasticsearch, helpers
import urllib3


es_host = "https://localhost:9200"
es_user = "elastic"
es_pass = "aeyi9Ok7raengoNgahlaK4neoghooz8O"
INDEX = "mastodon_v2" 

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

es = Elasticsearch(
    es_host,
    basic_auth=(es_user, es_pass),
    verify_certs=False,
    headers={
        "Accept": "application/vnd.elasticsearch+json; compatible-with=7",
        "Content-Type": "application/vnd.elasticsearch+json; compatible-with=7"
    }
)

total_result = {
    "size": 0,
    "aggs": {
        "same_urls": {
            "terms": {
                "field": "url",   
                "min_doc_count": 2,
                "size": 10000
            }
        }
    }
}
results = es.search(index=INDEX, body=total_result)
duplicate_urls = [bucket["key"] for bucket in results["aggregations"]["same_urls"]["buckets"]]

print(f"Found {len(duplicate_urls)} duplicate URLs...")

duplicate_list = []
for url in duplicate_urls:
    result = es.search(index=INDEX, body={
        "query": {
            "term": {
                "url": url  
            }
        }
    }, size=100)

    output = result["hits"]["hits"]
    for result in output[1:]:  
        duplicate_list.append({
            "_op_type": "delete",
            "_index": result["_index"],
            "_id": result["_id"]
        })

if duplicate_list:
    helpers.bulk(es, duplicate_list)
    print(f"Deleted {len(duplicate_list)} duplicates.")
else:
    print("No duplicates find.")
