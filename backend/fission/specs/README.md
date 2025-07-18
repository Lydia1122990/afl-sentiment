
Fission Specs
=============

This is a set of specifications for a Fission app.  This includes functions,
environments, and triggers; we collectively call these things "resources".

How to use these specs
----------------------

These specs are handled with the 'fission spec' command.  See 
```shell
fission spec --help
```

Use
```shell
fission spec apply
```
will "apply" all resources specified in this directory to your
cluster. That means it checks what resources exist on your cluster, what resources are
specified in the specs directory, and reconciles the difference by creating, updating or
deleting resources on the cluster.

'fission spec apply' will also package up your source code (or compiled binaries) and
upload the archives to the cluster if needed.  It uses 'ArchiveUploadSpec' resources in
this directory to figure out which files to archive.

You can use 
```shell
fission spec apply --watch
```
to watch for file changes and continuously keep
the cluster updated.

You can add YAMLs to this directory by writing them manually, but it's easier to generate
them.  
Use 
```shell
fission function create --spec
```
to generate a function spec,
```shell
fission environment create --spec
```
to generate an environment spec, and so on.

You can edit any of the files in this directory, except 'fission-deployment-config.yaml',
which contains a UID that you should never change.  To apply your changes simply use
'fission spec apply'.

fission-deployment-config.yaml
------------------------------

fission-deployment-config.yaml contains a UID.  This UID is what fission uses to correlate
resources on the cluster to resources in this directory.

All resources created by 'fission spec apply' are annotated with this UID. Resources on
the cluster that are _not_ annotated with this UID are never modified or deleted by
fission.

