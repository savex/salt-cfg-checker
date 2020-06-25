import json
import os
import platform
import sys
from copy import deepcopy
from multiprocessing.dummy import Pool
from subprocess import PIPE, Popen

_os = platform.system()
_packets = {}

_defaults = {
    "ip": None,
    "size": 0,
    "fragmentation": False,
    "count": 1,
    "exit_timeout": 1,
    "response_timeout": 1,
    "numeric": True
}

_help_message = \
    "Invalid parameters. Use: 'ping.py [PKT_SIZE] <IP>' or 'ping.py n.json'\n"

_template = {
    "returncode": -1,
    "stdout": "",
    "stderr": ""
}


def shell(command):
    _ps = Popen(
        " ".join(command),
        shell=True,
        stdout=PIPE,
        stderr=PIPE
    )
    _out = _ps.communicate()
    _err = _out[1]
    _out = _out[0]
    return _ps.returncode, _out, _err


def write_help():
    _t = deepcopy(_template)
    _t["returncode"] = 1
    _t["stderr"] = _help_message
    write_outcome(_t)


def write_outcome(_params):
    sys.stdout.write(json.dumps(_params))


def do_ping(_params):
    # Load params and defaults
    _d = deepcopy(_defaults)
    for key in _params:
        _d[key] = _params[key]

    # Build cmd
    _cmd = ["ping"]
    if _os == "Darwin":
        if not _d["fragmentation"]:
            _cmd.append("-D")
        if _d["exit_timeout"]:
            _cmd += ["-t", str(_d["exit_timeout"])]
    elif _os == "Linux":
        if not _d["fragmentation"]:
            _cmd += ["-M", "do"]
        if _d["exit_timeout"]:
            _cmd += ["-w", str(_d["exit_timeout"])]
    else:
        # Windows or other OS
        _t = deepcopy(_template)
        _t["returncode"] = 1
        _t["stderr"] = \
            "ping.py: '{}' support not implemented".format(_os)
        write_outcome(_t)
        sys.exit(1)

    if _d["size"]:
        _cmd += ["-s", str(_d["size"])]
    if _d["count"]:
        _cmd += ["-c", str(_d["count"])]
    if _d["numeric"]:
        _cmd.append("-n")
    if _d["response_timeout"]:
        _cmd += ["-W", str(_d["response_timeout"])]

    _cmd.append(_d["ip"])
    # sys.stdout.write("# {}\n".format(" ".join(_cmd)))
    _r, _out, _err = shell(_cmd)

    # TODO: parse results, latency, etc
    _t = deepcopy(_template)
    _t["returncode"] = _r
    _t["stdout"] = _out
    _t["stderr"] = _err
    _params.update(_t)
    return _params


def load_targets(filename):
    # load target ips from json
    with open(filename, "r") as f:
        j = json.load(f)

    return j


if len(sys.argv) < 2:
    # no params given
    write_help()
elif len(sys.argv) < 3:
    # one param: decide if it json file or IP
    _arg = sys.argv[1]
    if os.path.isfile(_arg):
        _packets = load_targets(_arg)
        # up to 15 packets at once
        pool = Pool(15)
        # prepare threaded map
        _param_map = []
        for _node, _data in _packets.items():
            if isinstance(_data, list):
                for target in _data:
                    _param_map.append(target)
            elif isinstance(_data, dict):
                _param_map.append(_data)
            else:
                _t = deepcopy(_template)
                _t["returncode"] = 1
                _t["stderr"] = \
                    "TypeError: 'list' or 'dict' expected. " \
                    "Got '{}': '{}'".format(
                        type(_data).__name__,
                        _data
                )
                _packets[_node] = _t
        _threaded_out = pool.map(do_ping, _param_map)
        for _out in _threaded_out:
            if isinstance(_packets[_out["tgt_host"]], dict):
                _packets[_out["tgt_host"]] = _out
            elif isinstance(_packets[_out["tgt_host"]], list):
                _packets[_out["tgt_host"]][_out["ip_index"]] = _out
        sys.stdout.write(json.dumps(_packets))
    else:
        # IP given
        _ip = sys.argv[1]
        write_outcome(do_ping(_ip))
elif len(sys.argv) < 4:
    # two params: size and IP
    _s = sys.argv[1]
    _ip = sys.argv[2]
    write_outcome(do_ping(_ip, size=_s))
else:
    # too many params given
    write_help()
