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

Set timer to trigger every day at 12pm
```shell
fission timetrigger create --spec --name scoretimer --function scoreharvester --cron "0 12 * * *"
```
Apply specs
```shell
fission spec apply
```