# Fission function for aflSubRed 

aflSubRed is a Python function that scrap subreddit subscriber counts via reddit api and then store into elasticsearch.

## Installation
 


Create spec yaml file
```shell
fission spec init
```
```shell
fission package create --spec --name aflsubred-pkg --source ./functions/aflSubRed/aflSubRed.py --source ./functions/aflSubRed/requirements.txt --env python39
```
```shell
fission fn create --spec --name aflsubred --pkg aflsubred-pkg --env python39 --entrypoint aflSubRed.main --secret elastic-secret --configmap shared-data 
```

```shell
fission route create --spec --name aflsubred-route --function aflsubred --url /aflsubred --method POST --createingress
```

Set up timer to run every 12 hours

```shell
fission timer create \
  --spec \
  --name aflsubred-timer \
  --function aflsubred \
  --cron "0 */12 * * *"
```
Apply specs
```shell
fission spec apply
```

Testing: Run below two functions, output "ok" should be return when function is successfully ran

```shell
fission fn test --name aflsubred
fission fn log -f --name aflsubred
```
