# Fission function for bluesky_post

`harvester-aflbluesky.py` is a Python function that searches Bluesky posts containing AFL team nicknames, performs sentiment analysis on the content, and stores the results in Elasticsearch.

## Installation

Create package:

    fission package create --spec \                   
    --name harvest-aflbluesky \    
    --source ../../backend/fission/functions/aflHarvester/harvest_aflbluesky.py \
    --source ../../backend/fission/functions/aflHarvester/requirements.txt \
    --env python39

Create function:

    fission function create --spec \
    --name harvest-aflbluesky \
    --pkg harvest-aflbluesky \
    --env python39 \
    --entrypoint "harvest_aflbluesky.main" \
    --secret elastic-secret

Create route:

    fission route create --spec --name harvest-aflbluesky --function harvest-aflbluesky \                            
    --method GET \                 
    --url '/harvest-aflbluesky'

Set up timer to run every 5 minutes:

    fission timer create --spec \             
    --name harvest-aflbluesky \
    --function harvest-aflbluesky \
    --cron "*/5 * * * *"

Apply specs:

    fission spec apply --specdir specs --wait

Test function:

    fission fn test --name harvest-aflbluesky --verbosity=2
    fission fn log -f --name harvest-aflbluesky
