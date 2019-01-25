import re
import sys
import subprocess
import json


def shell(command):
    _ps = subprocess.Popen(
        command.split(),
        stdout=subprocess.PIPE
    ).communicate()[0].decode()

    return _ps


def cut_option(_param, _options_list):
    _option = "n/a"
    _result_list = []
    if _param in _options_list:
        _index = _options_list.index(_param)
        _option = _options_list[_index+1]
        _l1 = _options_list[:_index]
        _l2 = _options_list[_index+2:]
        _result_list = _l1 + _l2
    else:
        _result_list = _options_list
    return _option, _result_list


def get_linked_devices(if_name):
    if '@' in if_name:
        _name = if_name[:if_name.index('@')]
    else:
        _name = if_name
    # identify device type
    _dev_link_path = shell('readlink /sys/class/net/{}'.format(_name))
    _type = "unknown"
    if len(_dev_link_path) > 0:
        _tmp = _dev_link_path.split('/')
        _tmp = _tmp[_tmp.index("devices") + 1]
        if _tmp.startswith("pci"):
            _type = "physical"
        elif _tmp.startswith("virtual"):
            _type = "virtual"

    # get linked devices if any
    _links = shell(
        "find /sys/class/net/{}/ -type l".format(_name)
    )
    # there can be only one parent device
    _lower = None
    # can be more than one child device
    _upper = None
    for line in _links.splitlines():
        _line = line.rsplit('/', 1)[1]
        if _line.startswith("upper_"):
            if not _upper:
                _upper = []
            _upper.append(_line[6:])
        elif _line.startswith("lower_"):
            if not _lower:
                _lower = []
            _lower.append(_line[6:])

    return _lower, _upper, _type


def get_ifs_data():
    _ifs_raw = shell('ip a')

    if_start = re.compile("^[0-9]+: .*: \<.*\> .*$")
    if_link = re.compile("^\s{4}link\/ether\ .*$")
    if_ipv4 = re.compile("^\s{4}inet\ .*$")

    _ifs = {}
    _if_name = None
    for line in _ifs_raw.splitlines():
        _if_data = {}
        if if_start.match(line):
            _tmp = line.split(':')
            _if_name = _tmp[1].strip()
            _if_options = _tmp[2].strip().split(' ')
            _lower, _upper, _type = get_linked_devices(_if_name)
            _if_data['order'] = _tmp[0]
            _if_data['mtu'], _if_options = cut_option("mtu", _if_options)
            _if_data['qlen'], _if_options = cut_option("qlen", _if_options)
            _if_data['state'], _if_options = cut_option("state", _if_options)
            _if_data['other'] = _if_options
            _if_data['ipv4'] = {}
            _if_data['mac'] = {}
            _if_data['type'] = _type
            _if_data['upper'] = _upper
            _if_data['lower'] = _lower
            _ifs[_if_name] = _if_data
        elif if_link.match(line):
            if _if_name is None:
                continue
            else:
                _tmp = line.strip().split(' ', 2)
                _mac_addr = _tmp[1]
                _options = _tmp[2].split(' ')
                _brd, _options = cut_option("brd", _options)
                _ifs[_if_name]['mac'][_mac_addr] = {}
                _ifs[_if_name]['mac'][_mac_addr]['brd'] = _brd
                _ifs[_if_name]['mac'][_mac_addr]['other'] = _options
        elif if_ipv4.match(line):
            if _if_name is None:
                continue
            else:
                _tmp = line.strip().split(' ', 2)
                _ip = _tmp[1]
                _options = _tmp[2].split(' ')
                _brd, _options = cut_option("brd", _options)
                # TODO: Parse other options, mask, brd, etc...
                _ifs[_if_name]['ipv4'][_ip] = {}
                _ifs[_if_name]['ipv4'][_ip]['brd'] = _brd
                _ifs[_if_name]['ipv4'][_ip]['other'] = _options

    return _ifs


ifs_data = get_ifs_data()

if len(sys.argv) > 1 and sys.argv[1] == 'json':
    sys.stdout.write(json.dumps(ifs_data))
else:
    _ifs = sorted(ifs_data.keys())
    _ifs.remove("lo")
    for _idx in range(len(_ifs)):
        _linked = ""
        if ifs_data[_ifs[_idx]]['lower']:
            _linked += "lower:{} ".format(
                ','.join(ifs_data[_ifs[_idx]]['lower'])
            )
        if ifs_data[_ifs[_idx]]['upper']:
            _linked += "upper:{} ".format(
                ','.join(ifs_data[_ifs[_idx]]['upper'])
            )
        _linked = _linked.strip()
        print("{0:8} {1:30} {2:18} {3:19} {4:5} {5:4} {6}".format(
            ifs_data[_ifs[_idx]]['type'],
            _ifs[_idx],
            ",".join(ifs_data[_ifs[_idx]]['mac'].keys()),
            ",".join(ifs_data[_ifs[_idx]]['ipv4'].keys()),
            ifs_data[_ifs[_idx]]['mtu'],
            ifs_data[_ifs[_idx]]['state'],
            _linked
        ))
