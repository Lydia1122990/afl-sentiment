# COMP90024 Team 54
```
NAME              STUDENT ID 

Xueying Yuan      1531588 

Shuangquan Zheng  1331085 

JunJie            1103084 

Hao Xu            1468277 

Chunmiao Zheng    1642700 
```


#### codebase	layout	(folders	and	subfolders)
```
.
├── README.md                               # Project overview and setup instructions
├── backend                                 # Backend services and serverless functions
│   ├── delete_duplicate_url.py
│   ├── fission                             # Fission functions (harvesting, cleaning, store etc.)
│   └── harvest_mastodon_publictransport.py
│   
├── data                                    # Any data you want to put in the code repository for manual insert
│   └── README.md
├── database                                # ElasticSearch type mappings, queries
│   └── README.md
├── docs                                    # Documentation  
│   └── README.md
├── env.yaml
├── frontend
│   ├── Data_visualisation.ipynb            # Frontend visualizations, notebooks, and user interface components
│   ├── README.md
│   └── fission                             # Fission functions (Mainly for data extraction from ElasticSearch database)
├── specs                                   # Kubernetes/Fission specs, secrets, and configuration files
│   ├── elastic-secret.yaml
│   └── shared-data.yaml
└── test                                    # Testing
    ├── 1st iter
    ├── 2nd iter
    ├── unit_test
    ├── README.md
    ├── requirements.txt
    ├── test_transharvester.py
    └── test_transobservations.py
```


Check all ElasticSearch pods are running before proceeding:

```shell
kubectl get pods -l release=elasticsearch -n elastic --watch
```

To check all service are created

```shell
kubectl get service -n elastic
```


## Fission Client

Mac & Linux

```shell
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
curl -Lo fission https://github.com/fission/fission/releases/download/v${FISSION_VERSION}/fission-v${FISSION_VERSION}-${OS}-amd64 \
   && chmod +x fission && sudo mv fission /usr/local/bin/
```




Note: on Apple M1-M4 microprocessors the architecture must be arm64 and not amd64


Mac (brew)

```shell
brew tap xxxbrian/tap
brew install fission-cli
```

### Validate the installation

```shell
fission check
```






Windows
For Windows, please use the Linux binary on WSL.

### Apply secret for elastic 

```shell
kubectl apply -f specs/elastic-secret.yaml
```
## Installation of elastic

```shell
export ES_VERSION="8.5.1"
helm repo add elastic https://helm.elastic.co
helm repo update
helm upgrade --install \
  --version=${ES_VERSION} \
  --create-namespace \
  --namespace elastic \
  --set replicas=2 \
  --set secret.password="elastic"\
  --set volumeClaimTemplate.resources.requests.storage="100Gi" \
  --set volumeClaimTemplate.storageClassName="perfretain" \
  elasticsearch elastic/elasticsearch
```
## Installation of Keda

Keda is a workload autoscaler for Kubernetes (it creates/removes pods depending on events).

```shell
export KEDA_VERSION='2.9'
helm repo add kedacore https://kedacore.github.io/charts
helm repo add ot-helm https://ot-container-kit.github.io/helm-charts/
helm repo update
helm upgrade keda kedacore/keda --install --namespace keda --create-namespace --version ${KEDA_VERSION}
```

## Installation of Redis
Redis is a key-value store used to store messages for Fission.

```shell
export REDIS_VERSION='0.19.1'
helm repo add ot-helm https://ot-container-kit.github.io/helm-charts/
helm upgrade redis-operator ot-helm/redis-operator \
    --install --namespace redis --create-namespace --version ${REDIS_VERSION}
    
kubectl create secret generic redis-secret --from-literal=password=password -n redis
helm upgrade redis ot-helm/redis --install --namespace redis   
```

Wait for all pods to have started:
```shell
kubectl get pods -n keda --watch
```

```shell
kubectl get pods -n redis --watch
```

### Create index for elasticsearch if requried
```shell
curl -X PUT "http://elasticsearch-master.elastic.svc.cluster.local:9200/{index-name}" \
-H 'Content-Type: application/json' \
-u username:password \
-k
```