from elasticsearch import Elasticsearch

es = Elasticsearch(
    hosts=["https://localhost:9200"],
    basic_auth=("elastic", "aeyi9Ok7raengoNgahlaK4neoghooz8O"),
    verify_certs=False,
)

print(es.info())
