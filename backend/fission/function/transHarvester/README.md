# Fission function for transHarvester 

transHarvester is a Python function to take a job containing subreddit name and limit number from redis queue. Once received it will scrape subreddit calculated it's sentment value and then call addElastic function to store into elasticserach.

## Installation

Create spec yaml file
```shell
fission spec init
```
```shell
fission package create --spec --name transharvester-pkg --env python39 --source ./function/transHarvester/transHarvester.py --source ./function/transHarvester/requirements.txt 
```
```shell
fission function update --spec --name transharvester-reddit --env python39 --code ./function/transHarvester.py --entrypoint transHarvester.main --pkg transharvester-pkg --secret elastic-secret
```

```shell
fission route create --spec --url /transharvester --function transharvester-reddit --name transharvester-reddit-route --method POST --createingress
```

Apply specs
```shell
fission spec apply
```

Test
```shell
fission function test --name transharvester-reddit