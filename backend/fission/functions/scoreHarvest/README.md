# Fission function for scoreHarvest 

scoreHarvest is a Python function scrape data via squiggle API and store into elastic.

## Installation  

Create spec yaml file
```shell
fission spec init
```
```shell
fission package create --spec --name scoreharvester-pkg --source ./functions/scoreHarvest/scoreHarvester.py --source ./functions/scoreHarvest/requirements.txt --env python39
```
```shell
fission fn create --spec --name scoreharvester --pkg scoreharvester-pkg --env python39 --entrypoint scoreHarvester.main --secret elastic-secret
```

```shell
fission route create --spec --name scoreharvester-route --function scoreharvester --url /scoreharvester --method POST --createingress
``` 

Set timer to trigger every day at 12pm
```shell
fission timetrigger create --spec --name scoretimer --function scoreharvester --cron "0 12 * * *"
```
Apply specs
```shell
fission spec apply
```