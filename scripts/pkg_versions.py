import sys
import subprocess
import json

from multiprocessing.dummy import Pool


def shell(command):
    _ps = subprocess.Popen(
        command.split(),
        stdout=subprocess.PIPE
    ).communicate()[0].decode()

    return _ps


def get_versions(pkg):
    # get the info for the package
    _pkg_info = shell('apt-cache policy ' + pkg)

    _installed = 'none'
    _candidate = 'none'

    # extract the installed and candidate
    for line in _pkg_info.splitlines():
        if line.find("Installed") > 0:
            _installed = line.split(':', 1)[1].strip()
        elif line.find("Candidate") > 0:
            _candidate = line.split(':', 1)[1].strip()
    return [pkg, _installed, _candidate, _pkg_info]


# get list of packages
_list = shell("apt list --installed")
pkg_list = _list.splitlines()
pkg_list = [_pkg.split('/')[0] for _pkg in pkg_list[1:]]

# threading pool
pool = Pool(10)

result = pool.map(get_versions, pkg_list)

# init pkg storage
pkgs = {}
for res in result:
    _pkg = res[0]
    if _pkg not in pkgs:
        pkgs[_pkg] = {}
    pkgs[_pkg]['installed'] = res[1]
    pkgs[_pkg]['candidate'] = res[2]
    pkgs[_pkg]['raw'] = res[3]

buff = json.dumps(pkgs)
sys.stdout.write(buff)
