#!/bin/bash 

# add command if new items need to be deleted.

# Delete routes
fission route delete --name addelastic-route
fission route delete --name aflsubred-route
fission route delete --name afl-harvester-route
fission route delete --name aharvester-route
fission route delete --name checkelastic-route
fission route delete --name cleantext-route
fission route delete --name enqueue
fission route delete --name scoreharvester-route

# Delete functions
fission fn delete --name aflsubred
fission fn delete --name aharvester
fission fn delete --name checkelastic
fission fn delete --name enqueue
fission fn delete --name textclean
fission fn delete --name scoreharvester

# Delete packages
fission pkg delete --name aflsubred-pkg
fission pkg delete --name aharvester-pkg
fission pkg delete --name checkelastic-pkg
fission pkg delete --name enqueue-pkg
fission pkg delete --name textclean-pkg
fission pkg delete --name scoreharvester-pkg
fission pkg delete --name elastic-pkg

# Delete triggers
fission mqt delete --name afl-harvesting
fission timer delete --name aflsubred-timer
fission timer delete --name aharvester-timer
fission timer delete --name scoretimer