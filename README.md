# salt-cfg-checker
This checker module is used to verify and validate cloud
after the deployment using number of routines to create reports

# Local run
It is pretty simple: 
- deploy on cfg node, using root creds, on /root/
```bash
git clone https://github.com/savex/salt-cfg-checker
cd salt-cfg-checker
virtualenv .cfgcheck
source .cfgcheck/bin/activate
pip install -r requirements.txt
```
- you can check your local.env file for parameters (no need to update for running on cfg node)
- packages report (HTML): `mcp_check packages report --html cloud-packages.html`
- packages report (CSV): `mcp_check packages report --csv cloud-packages.csv`

# External cloud
You can also create your env file to connect to env
 - create your *.env file
   or supply environment vars to module other way
 - in the `env` file set host and user for SSH. 
   For options, use your `~/.ssh/config`
 - if node listing fails, execute `salt-key` on master 
   and create an `etc/nodes.list` file with minions list

# Version history
- [*Done*] Update messages to same style
- [*Done*] Release versions support with customizable updates
- [*Done*] Upgrades, errors and downgrades detection
- [*Done*] Proper Debian package [version](https://www.debian.org/doc/debian-policy/ch-controlfields.html#version) naming convention support

TODO:
- Check root on startup, exit
- Prepare script to create venv
- Format reclass compare file


Cheers!
