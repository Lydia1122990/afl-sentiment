# Fission function for enqueue 

Enqueue is a Python function recevies message from other fission function and once recieved it will add jobs to the redis queue for harvester to action.

## Installation 
 

 

Create spec yaml file
```shell
fission spec init
```
```shell
fission package create --spec --name enqueue-pkg --source ./functions/enqueue/__init__.py --source ./functions/enqueue/enqueue.py --source ./functions/enqueue/requirements.txt --source ./functions/enqueue/build.sh --env python39 --buildcmd './build.sh'
```
```shell
fission fn create --spec --name enqueue --pkg enqueue-pkg --env python39 --entrypoint enqueue.main --secret elastic-secret --configmap shared-data 
```

```shell
fission httptrigger create --spec --name enqueue --url "/enqueue/{topic}" --method POST --function enqueue
``` 
Apply specs
```shell
fission spec apply
```