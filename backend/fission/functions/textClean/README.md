Move tho this folder and run below code to create function

```
zip -r textclean.zip textClean.py requirements.txt
```
```
fission package create --name text-clean-pkg \
  --env python39 \
  --sourcearchive textclean.zip 
``` 

```
fission fn create --name text-clean \
  --env python39 \
  --pkg text-clean-pkg \
  --entrypoint "textClean.main"     
```
If changes are made to the function then run below code

```
zip -r textclean.zip textClean.py requirements.txt
```

Update package
```
fission pkg update --name text-clean-pkg --sourcearchive textclean.zip
```

Update function

```
fission fn update --name text-clean --entrypoint "textClean.main"
```