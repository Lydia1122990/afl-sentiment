# Fission function for aHarvester 

aHarvester is a Python function send message to enqueue function via Fission router to trigger aflHarvest function

## Installation 

Create spec yaml file
```shell
fission spec init
```
```shell
fission package create --spec --name aharvester-pkg --source ./functions/aHarvester/__init__.py --source ./functions/aHarvester/aharvester.py --source ./functions/aHarvester/requirements.txt --source ./functions/aHarvester/build.sh --env python39 --buildcmd './build.sh'
```
```shell
fission fn create --spec --name aharvester --pkg aharvester-pkg --env python39 --entrypoint aHarvester.main 
```

```shell
fission route create --spec --url /aharvester --function aharvester --name aharvester-route --createingress
```

Set up timer to trigger function every 5 minutes

```shell
fission timer create --spec --name aharvester-timer --function aharvester --cron "@every 5m"
```
Apply specs
```shell
fission spec apply
```