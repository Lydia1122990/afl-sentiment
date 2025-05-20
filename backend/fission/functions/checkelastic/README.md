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

Testing: Follow steps in [tests](https://gitlab.unimelb.edu.au/junjwang3/comp90024-team-54/-/tree/main/test?ref_type=heads) folder to activate venv and run below command to test checkelastic

1st Iteration folder: [test](https://gitlab.unimelb.edu.au/junjwang3/comp90024-team-54/-/tree/main/test/1st%20iter/test?ref_type=heads)
```shell
python end2end.py
```
Upon successful execution terminal output should show test successful indication connection is established

2nd Iteration folder: [test](https://gitlab.unimelb.edu.au/junjwang3/comp90024-team-54/-/tree/main/test/2nd%20iter?ref_type=heads)
```shell
python end2end.py
```
Upon successful execution payload should be added be cleaned and terminal output will show test successful