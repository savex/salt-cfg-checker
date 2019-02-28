# salt-cfg-checker
This checker module is used to verify and validate cloud
after the deployment using number of routines to create reports

# Local run
It is pretty simple: 
- deploy on cfg node
- check your local.env file for parameters
- ...run: `cfg_check -h`

# External cloud
Be sure to 
 - create your *.env file
   or supply environment vars to module other way
 - in the `env` file set host and user for SSH. 
   For options, use your `~/.ssh/config`
 - if node listing fails, execute `salt-key` on master 
   and create an `etc/nodes.list` file with minions list

To be updated.

Cheers!

