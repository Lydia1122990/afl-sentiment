# Fission function for bluesky_post

`harvester-aflbluesky.py` is a Python function that searches Bluesky posts containing AFL team nicknames, performs sentiment analysis on the content, and stores the results in Elasticsearch.

## Installation

fission package create \                                    --spec \                   
  --name harvest-aflbluesky \    
  --source ../../backend/fission/functions/aflHarvester/harvest_aflbluesky.py \
  --source ../../backend/fission/functions/aflHarvester/requirements.txt \
  --env python39

fission function create --spec \
  --name harvest-aflbluesky \
  --pkg harvest-aflbluesky \
  --env python39 \
  --entrypoint "harvest_aflbluesky.main" \
  --secret elastic-secret

fission route create --spec --name harvest-aflbluesky --function harvest-aflbluesky \                            
  --method GET \                 
  --url '/harvest-aflbluesky'
  
fission timer create --spec \             
  --name harvest-aflbluesky \
  --function harvest-aflbluesky \
  --cron "*/5 * * * *"