# Fission function for bluesky_fan

`bluesky_fan` is a Python function that retrieves follower counts from AFL team accounts on [Bluesky](https://bsky.social) and stores the data into an Elasticsearch index.

## Installation

Create spec yaml file:

    fission spec init

Create package:

    fission package create --spec --name fanpkg \
      --source ./functions/bluesky_fan/blueskyfan.py \
      --source ./functions/bluesky_fan/requirements.txt \
      --source ./functions/bluesky_fan/build.sh \
      --env python39 \
      --buildcmd './build.sh'

Create function:

    fission function create --spec --name fanpkg \
      --pkg fanpkg \
      --env python39 \
      --entrypoint "fanpkg.main"
      --secret elastic-secret

Create route:

    fission route create --spec --name fanpkg --function fanpkg \
      --method GET \
      --url '/fanpkg'

Set up timer to run every 12 hours:

    fission timer create --spec \
      --name fanpkg \
      --function fanpkg \
      --cron "0 */12 * * *"

Apply specs:

    fission spec apply --specdir specs --wait

Test function:

    fission fn test --name fanpkg --verbosity=2
