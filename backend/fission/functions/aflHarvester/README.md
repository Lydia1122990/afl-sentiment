# Fission function for aflHarvester 

aflHarvester is a Python function to take a job containing subreddit name and limit number from redis queue. Once received it will scrape subreddit calculated it's sentment value and then call addElastic function to store into elasticserach.

## Installation

Create spec yaml file
```shell
fission spec init
```
```shell
fission package create --spec --name elastic-pkg --source ./functions/addelastic/addelastic.py --source ./functions/addelastic/requirements.txt --env python39 
```
```shell
fission fn create --spec --name addelastic --pkg elastic-pkg --env python39 --entrypoint addelastic.main --specializationtimeout 180 --secret elastic-secret 
```

```shell
fission route create --spec --name addelastic-route --function addelastic --url /addelastic --method POST --createingress
```

Apply specs
```shell
fission spec apply
```