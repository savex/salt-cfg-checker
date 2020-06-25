# salt-cfg-checker
This checker module is used to verify and validate cloud
after the deployment using number of routines to create reports

# Background.
Many of our deployments comes with the monitoring solutions, but none of them keeps track of the package versions that is included in release.
nd it is very important to have proper package versions. That is critical for cloud stability.
here is more, it is critical to keep track of configuration values for networks (and others too..) in Runtime, in Configuration and at Reclass.
Also, it is important to keep track of the changes in reclass and be able to have tool that gives clear report on what has been changed.

So, this tool here that can do some checks on the cloud that will be handy for:
- Engineers that deployed the clouds and need to be sure that proper versions installed on every node
- Services Team to check cloud at deploy time
- ProdCare engineers that is supporting client environments
- Support team

Main use cases for the MCP-checker is:
- Generate a package versions report that will show which package versions must be payed attention on: Installed vs Candidates vs Release Notes. This will really help on understanding if some node has some strangely versioned package
- Generate network check against running nodes to collect IPs, mach them into subnets and check MTUs in Runtime (ip a) vs reclass configuration
- Compare two reclass models recursively (folder1 vs folder2) and generate differences report.

# Installation
It is pretty simple: 
- deploy on cfg node, using root creds, on /root/
```bash
git clone http://gerrit.mcp.mirantis.com/mcp/cfg-checker
cd cfg-checker
virtualenv .cfgcheck
source .cfgcheck/bin/activate
pip install -r requirements.txt
```
- you can check your local.env file for parameters (no need to update for running on cfg node)

# Running
- Packages report (HTML): `mcp_check packages report --html __packages_html_filename.html__`
- Packages report (CSV): `mcp_check packages report --csv __packages_csv_filename.csv__`
- Network check (CLI output): `mcp-checker network check`
- [Work in progress] Network check (HTML report): `mcp-checker network report --html __network_html_filename.html__`
- List folders that can be used for Reclass Compare: `mcp-checker reclass list -p __models_path__`
- Compare two Reclass models (file and parameter wise): `mcp-checker reclass diff --model1 __model1_path__ --model2 __model2_path__ --html __reclass_html_filename.html__`

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
- [*Done*] Refactor parameter handling to have same naming for same options in different sections
- [*Done*] Remove unneeded data from report
- [*Done*] Add progress bar when processing along with handy stats
- [*Done*] Add possibility to check cloud remotely
- [*Done*] Add possibility to have several ready to use cloud connection configurations
- [*Done*] Use flexible plugin structure to execute modules

TODO:
- Check root on startup, exit
- Prepare script to create venv
- Reformat reclass compare file
- Finalize Network check HTML report
- Do simple rule-based checks on network
- Implement simple packet sniff mechanics to check node-node VCP trafic flow
- Add node params to output
- Format reclass compare file


Cheers!
