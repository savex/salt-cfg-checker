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


def get_ifs_data():
    _ifs_raw = shell('ip a')

    if_start = re.compile("^[0-9]+: .*: \<.*\> .*$")
    if_ipv4 = re.compile("^\s{4}inet\ .*$")

    _ifs = {}
    _if_name = None
    for line in _ifs_raw.splitlines():
        _if_data = {}
        if if_start.match(line):
            _tmp = line.split(':')
            _if_name = _tmp[1].strip()
            _if_options = _tmp[2].strip().split(' ')
            _if_data['order'] = _tmp[0]
            _if_data['mtu'], _if_options = cut_option("mtu", _if_options)
            _if_data['qlen'], _if_options = cut_option("qlen", _if_options)
            _if_data['state'], _if_options = cut_option("state", _if_options)
            _if_data['other'] = _if_options
            _if_data['ipv4'] = {}
            _ifs[_if_name] = _if_data
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

# _ifs = sorted(ifs_data.keys())
# _ifs.remove("lo")
# for _idx in range(len(_ifs)):
#     print("\t{}:\t{},\t\t{},\t{}".format(
#         _ifs[_idx],
#         " ".join(ifs_data[_ifs[_idx]]['ipv4'].keys()),
#         ifs_data[_ifs[_idx]]['mtu'],
#         ifs_data[_ifs[_idx]]['state']
#     ))


buff = json.dumps(ifs_data)
sys.stdout.write(buff)
