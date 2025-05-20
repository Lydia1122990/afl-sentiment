# Debugging & Initalisation

Check package

```shell
fission pkg info --name <package name>
```

Creating Specs for environment


```shell
fission specs init
``` 

Create Python 3.9 environment 

```shell
fission env create --spec --name python39 --image fission/python-env-3.9 --builder fission/python-builder-3.9
```

Check if there's errors

```shell
fission spec validate
```

If no errors can run below to apply specs to cluster 

```shell
fission spec apply --specdir fission/specs --wait
```

or if you want to apply single file for example

```shell
kubectl apply -f ./specs/{filename}.yaml
``` 

To apply all specificiation in specs folder

```shell
fission spec apply --specdir specs --wait --force
```
## Start port forward

### Elasticsearch

```shell
kubectl port-forward service/elasticsearch-master -n elastic 9200:9200
```
### Fission route
```shell
kubectl port-forward service/router -n fission 9090:80
```
### Kibana
```shell
kubectl port-forward service/kibana-kibana -n elastic 5601:5601
```
### Redis
```shell
kubectl port-forward service/redis-insight --namespace redis 5540:5540
```

### Delete all package, route, triggers
```shell
source ./build.sh
```

