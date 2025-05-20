Move tho this folder and run below code to create function

```
zip -r textclean.zip textClean.py requirements.txt
```
```

``` 

```
  
```
If changes are made to the function then run below code

```
zip -r textclean.zip textClean.py requirements.txt
```



# Fission function for textClean 

textClean is a Python function recieve text via HTTP and clean the text.

## Installation  
 

Create zip folder
```shell
zip -r textclean.zip textClean.py requirements.txt
```
```shell
fission package create --name text-clean-pkg \
  --env python39 \
  --sourcearchive textclean.zip 
```
```shell
fission fn create --name text-clean \
  --env python39 \
  --pkg text-clean-pkg \
  --entrypoint "textClean.main"   
```

```shell
fission route create --spec --name textclean-route --function text-clean --url /text-clean --method POST --createingress
``` 

### If require update
Update package
```
fission pkg update --name text-clean-pkg --sourcearchive textclean.zip
```

Update function

```
fission fn update --name text-clean --entrypoint "textClean.main"
```

Apply specs
```shell
fission spec apply
```
 
Testing: Follow steps in [tests](https://gitlab.unimelb.edu.au/junjwang3/comp90024-team-54/-/tree/main/test?ref_type=heads) folder to activate venv and run below command to test textClean

1st Iteration folder: [test](https://gitlab.unimelb.edu.au/junjwang3/comp90024-team-54/-/tree/main/test/1st%20iter/test?ref_type=heads)
```shell
python end2end.py
```
Upon successful executaiton terminal output should show test successful indication connection is established

2nd Iteration folder: [test](https://gitlab.unimelb.edu.au/junjwang3/comp90024-team-54/-/tree/main/test/2nd%20iter?ref_type=heads)
```shell
python end2end.py
```
Upon successful executaiton payload should be added be cleaned and terminal output will show test successful
