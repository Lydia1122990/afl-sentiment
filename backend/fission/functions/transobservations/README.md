# Fission function for transobservations

transobservations is a Python function that scrap subreddit subscriber counts via reddit api and then store into elasticsearch.

## Installation

Create spec yaml file
```shell
fission spec init
```
```shell
fission package create --spec --name transobservations-pkg --env python39 --source ./function/transobservations/transobservations.py --source ./function/transobservations/requirements.txt
```
```shell
fission function create --spec --name transobservations --env python39 --code ./function/transobservations/transobservations.py --entrypoint transobservations.main --pkg transobservations-pkg --secret elastic-secret
```

```shell
fission route create --spec --name transobservations --function transobservations --url /atransobservations --method POST --createingress
```

Set up timer to run every 10 minutes

```shell
fission timer create --spec --name transobservations --function transobservations --cron "@every 10m"
```
Apply specs
```shell
fission spec apply
```

Test
```shell
fission function test --name transobservations
```