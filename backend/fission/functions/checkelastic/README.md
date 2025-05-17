# Fission function for checkelastic 

checkelastic is a Python function checks if the item already existed in the index.

## Installation 
 
 

Create spec yaml file
```shell
fission spec init
```
```shell
fission package create --spec --name checkelastic-pkg --source ./functions/checkelastic/__init__.py --source ./functions/checkelastic/checkelastic.py --source ./functions/checkelastic/requirements.txt --source ./functions/checkelastic/build.sh --env python39 --buildcmd './build.sh'
```
```shell
fission fn create --spec --name checkelastic --pkg checkelastic-pkg --env python39 --entrypoint checkelastic.main --specializationtimeout 180 --secret elastic-secret  
```

```shell
fission route create --spec --name checkelastic-route --function checkelastic --url /checkelastic --method POST --createingress
``` 
Apply specs
```shell
fission spec apply
```