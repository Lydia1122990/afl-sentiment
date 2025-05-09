Can use for debugging

Check package
``fission pkg info --name <package name>``

Creating Specs 


``fission specs init`` 

Create Python 3.9 environment 

``fission env create --spec --name python39 --image fission/python-env-3.9 --builder fission/python-builder-3.9``

Check if there's errors

``fission spec validate``

If no errors can run below to apply specs to cluster 

``fission spec apply --specdir fission/specs --wait``

or if you want to apply single file for example

``kubectl apply -f ./specs/env-python39.yaml.yaml``

Creating function for textClean
```yaml
fission package create --spec --name textclean-pkg --source ./functions/textClean/textClean.py --source ./functions/textClean/requirements.txt --env python39 

fission fn create --spec --name textclean --pkg textclean-pkg --env python39 --entrypoint textClean.main

fission route create --spec --name cleantext-route --function textclean --method POST --url /text-clean --createingress
``` 

To apply all specificiation in specs folder

```
fission spec apply --specdir specs --wait --force
```
