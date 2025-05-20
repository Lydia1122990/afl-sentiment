# COMP90024 Team 54

## Software Stack Installation
### Pre-requirements

OpenStack clients >= 5.8.x ([Installation instructions](https://docs.openstack.org/newton/user-guide/common/cli-install-openstack-command-line-clients.html)).

Not: Please ensure the following Openstack clients are installed: python-cinderclient, python-keystoneclient, python-magnumclient, python-neutronclient, python-novaclient, python-octaviaclient. See: [Install the OpenStack client](https://docs.openstack.org/newton/user-guide/common/cli-install-openstack-command-line-clients.html).


JQ >= 1.7.x ([Installation instructions](https://jqlang.github.io/jq/download/)).
kubectl >= 1.30.0 and < 1.33.0 ([Installation instructions](https://kubernetes.io/docs/tasks/tools/)).
Helm >= 3.17.x ([Installation instructions](https://helm.sh/docs/intro/install/)).
MRC project with enough resources to create a Kubernetes cluster.


## Client Configuration


Log in to the MRC (or Nectar) Dashboard with your University of Melbourne credentials and select the project you want to use (unimelb-comp90024-54-2025).



Download the OpenStack RC file from the User menu.



Obtain the Openstack password from User -> Settings menu, click on Reset Password on the left and save the password in a safe place.



Source the OpenStack RC file downloaded in step 2 in your terminal and enter the password obtained in step 3 when prompted.



Note: Password will not be displayed on the screen when typed.


```shell
source ./unimelb-comp90024-54-2025-openrc.sh
```





Click Project -> Compute -> Key Pairs -> Create Key Pair and create a new key pair named mykeypair (replace mykeypair with the name you prefer) and import the public key. Keep the private key file downloaded (e.g. mykeypair.pem) in a safe place.




All team members must have their key pairs created and the public key file added to the project (see the previous step).


- Check whether the cluster has been created healthy (it may take more than 15 minutes).

```shell
openstack coe cluster show comp90024 --fit-width
```

## Check whether the cluster has been created healthy (it may take more than 15 minutes).

```
openstack coe cluster show comp90024 --fit-width
```

> Note: status should be CREATE_COMPLETE, health_status should be HEALTHY and coe_version should be v1.31.1

Move the config file to .kube (you may need to craete .kube folder)

```shell
mv config ~/.kube/config
chmod 600 ~/.kube/config
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