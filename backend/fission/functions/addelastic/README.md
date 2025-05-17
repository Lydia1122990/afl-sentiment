# Fission function for add Elastic 

addelastic is a Python function to take data and store into elasticserach.

## Installation

Create spec yaml file
```shell
fission spec init
``` 



```shell
fission package create --spec --name aflharvester-pkg --source ./functions/aflHarvester/aflHarvester.py --source ./functions/aflHarvester/requirements.txt --env python39 
```

```shell
fission fn create --spec --name aflharvester --pkg aflharvester-pkg --env python39 --entrypoint aflHarvester.main --specializationtimeout 180 --secret elastic-secret
```

```shell
fission route create --spec --name afl-harvester-route --function aflharvester --url /aflharvester --method POST --createingress
```

Create mtrigger for queue

```shell
(
    cd fission
    fission mqtrigger create --name afl-harvesting \
    --spec \
    --function aflharvester \
    --mqtype redis \
    --mqtkind keda \
    --topic afl \
    --errortopic errors \
    --maxretries 3 \
    --metadata address=redis-headless.redis.svc.cluster.local:6379 \
    --metadata listLength=100 \
    --metadata listName=afl:subreddit 
    )  
```


Apply specs
```shell
fission spec apply
```