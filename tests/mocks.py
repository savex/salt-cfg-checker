import json
import os

from tests.test_base import tests_dir


# Prepare fake filenames and files
_res_dir = os.path.join(tests_dir, 'res')


# preload file from res
def _load_from_res(_filename, mode='rt'):
    fake_file_path = os.path.join(_res_dir, _filename)
    _patch_buf = []
    with open(fake_file_path, mode) as _f:
        _patch_buf = _f.read()

    return _patch_buf


_fakepage_template = _load_from_res(os.path.join(_res_dir, "_fakepage.html"))
_fakepage_empty = _load_from_res(os.path.join(_res_dir, "_fakeempty.html"))
_fake_keys = json.loads(_load_from_res("_fake_keys.json"))
_fake_pkg_versions = _load_from_res("_fake_pkg_versions.json")
_fake_network_data = _load_from_res("_fake_net_data.json")


def _prepare_result_for_target(_tgt, result=True):
    # prepare True answer for target node if we have it in fakes list
    _nodes = _fake_keys["return"]["minions"]
    _m = {}
    if _tgt == "*":
        for _n in _nodes:
            _m[_n] = result
    elif _tgt in _nodes:
        # single target
        _m[_tgt] = result
    elif " or " in _tgt:
        # compund
        _t_list = _tgt.split(" or ")
        for _t in _t_list:
            _m[_t] = result
    return _m


class MockResponse:
    def __init__(self, _buffer, status_code):
        if _buffer is None:
            self.content = _buffer
            self.text = _buffer
            self.json = _buffer
        elif isinstance(_buffer, bytes):
            self.content = _buffer
            self.text = None
            self._json = None
        elif isinstance(_buffer, dict):
            _dump = json.dumps(_buffer)
            self.content = _dump.encode('utf-8')
            self.text = _dump
            self._json = _buffer
        else:
            self.content = _buffer.encode('utf-8')
            self.text = _buffer
            self._json = None

        self.status_code = status_code
        self.reason = "OK" if self.status_code == 200 else "FAIL"

    def content(self):
        return self.content

    def text(self):
        return self.text

    def json(self):
        if not self._json:
            try:
                _j = json.loads(self.text)
            except Exception:
                raise Exception("Failed to create json {}".format(self.text))
            return _j
        else:
            return self._json

    def reason(self):
        return self.reason

    def ok(self):
        return True if self.status_code == 200 else False

    def cookies(self):
        return None


def mocked_salt_post(*args, **kwargs):
    _rest_handle = args[0].split('/', 3)[3]
    if _rest_handle == "login":
        # return fake token
        _fake_token = {
            "return":
            [
                {
                    "perms": [
                        ".*",
                        "@local",
                        "@wheel",
                        "@runner",
                        "@jobs"
                    ],
                    "start": 0,
                    "token": "faketoken",
                    "expire": 0,
                    "user": "salt",
                    "eauth": "pam"
                }
            ]
        }

        return MockResponse(_fake_token, 200)
    elif not _rest_handle and "json" in kwargs:
        # handle functions
        _funs = kwargs["json"]
        if isinstance(_funs, list):
            if len(_funs) > 1:
                raise Exception("Multiple commands in sale requiest")
            else:
                _f = _funs[0]
        _t = _f["tgt"]
        _a = _f["arg"] if "arg" in _f else ""
        _f = _f["fun"]
        if _f == "test.ping":
            # prepare answer to ping
            _val = _prepare_result_for_target(_t)
            return MockResponse({"return": [_val]}, 200)
        elif _f == "pillar.get":
            # pillar get response, preload data
            _j = json.loads(_load_from_res("_fake_pillars.json"))
            _result = {"return": []}
            if _t in _j.keys():
                # target is single
                _j = _j[_t]
                _r = {_t: _j[_a]} if _a in _j else {}
            else:
                # target is a compound
                _t_list = _t.split(" or ")
                _r = {}
                for _t in _t_list:
                    _val = _j[_t][_a] if _a in _j[_t] else {}
                    _r[_t] = _val
            _result["return"].append(_r)
            return MockResponse(_result, 200)
        elif _f == "cmd.run":
            # determine which script is called
            _args = _a.split()
            if _args[0] == "python" and _args[1].endswith("pkg_versions.py"):
                _val = _prepare_result_for_target(_t, _fake_pkg_versions)
            elif _args[0] == "python" and _args[1].endswith("ifs_data.py"):
                _val = _prepare_result_for_target(_t, _fake_network_data)
            elif _args[0] == "uname":
                _val = _prepare_result_for_target(_t, "FakeLinux")
            elif _args[0] == "lscpu":
                _val = _prepare_result_for_target(
                    _t,
                    _load_from_res("_fake_lscpu.txt")
                )
            elif _args[0] == "free":
                _val = _prepare_result_for_target(
                    _t,
                    "Mem: 1.9G 1.4G 84M 22M 524M 343M"
                )
            elif _args[0] == "df":
                _val = _prepare_result_for_target(
                    _t,
                    _load_from_res("_fake_df.txt")
                )
            elif _args[0] == "service":
                _val = _prepare_result_for_target(
                    _t,
                    _load_from_res("_fake_service_status.txt")
                )
            elif _args[0] == "virsh":
                _val = _prepare_result_for_target(
                    _t,
                    _load_from_res("_fake_kvm_instances.txt")
                )
            elif _args[0] == "cat" and \
                    _args[1].endswith("/proc/net/softnet_stat;"):
                _val = _prepare_result_for_target(
                    _t,
                    _load_from_res("_fake_softnet_stats.txt")
                )
            return MockResponse({"return": [_val]}, 200)
        elif _f in ["file.mkdir", "file.touch", "file.write", "cp.get_file"]:
            _val = _prepare_result_for_target(_t)
            return MockResponse({"return": [_val]}, 200)

    return MockResponse(None, 404)


def mocked_salt_get(*args, **kwargs):
    _rest_handle = args[0].split('/', 3)[3]
    if _rest_handle == "keys":
        # return list of minions
        _fake_keys = _load_from_res("_fake_keys.json")
        return MockResponse(_fake_keys, 200)
    elif _rest_handle == "minions":
        # list of minions
        _list = _load_from_res("_fake_minions.json")
        return MockResponse(_list, 200)
    return MockResponse(None, 404)


def mocked_package_get(*args, **kwargs):
    # fake page _placeholder_
    _placeholder = "_placeholder_"
    _type = "_type_"
    # fake domain
    _url = "http://fakedomain.com"
    # folders list and file
    _folders = [
        "2099.0.0",
        "ubuntu",
        "dists",
        "trusty",
        "main",
        "binary-amd64"
    ]
    _file = "Packages.gz"

    # if this is a fakedomain for mirrors
    if args[0].startswith(_url):
        # cut url
        _u = args[0].replace(_url, "")
        # detect folder
        _split_res = _u.rsplit('/', 2)
        if len(_split_res) > 2 and _u[-1] != '/':
            _current_page = _u.rsplit('/', 2)[2]
        else:
            _current_page = _u.rsplit('/', 2)[1]
        # if this is main index page, take first
        if len(_current_page) == 0:
            # initial folder
            _p = _fakepage_template
            _p = _p.replace(_placeholder, _folders[0] + "/")
            _p = _p.replace(_type, "-")
            # return fake page
            return MockResponse(_p, 200)
        # index in array
        elif _current_page in _folders:
            # simulate folder walk
            _ind = _folders.index(_current_page)
            # get next one
            if _ind+1 < len(_folders):
                # folder
                _p = _fakepage_template
                _p = _p.replace(_placeholder, _folders[_ind+1] + "/")
                _p = _p.replace(_type, "-")
            else:
                # file
                _p = _fakepage_template
                _p = _p.replace(_placeholder, _file)
                # type is detected as '-' for folder
                # and <number> for file
                _p = _p.replace(_type, "999")
            # supply next fake page
            return MockResponse(_p, 200)
        elif _current_page == _file:
            # just package.gz file
            # preload file
            _gzfile = _load_from_res("Packages.gz", mode='rb')
            return MockResponse(_gzfile, 200)
        elif _current_page == "hotfix" or _current_page == "update":
            return MockResponse(_fakepage_empty, 200)

    return MockResponse(None, 404)


_shell_salt_path = "cfg_checker.common.salt_utils.shell"


def mocked_shell(*args, **kwargs):
    _args = args[0].split()
    # _fake_salt_response = ["cfg01.fakedomain.com"]
    _args = _args[1:] if _args[0] == "sudo" else _args
    if _args[0].startswith("salt-call"):
        # local calls
        _json = {"local": None}
        if _args[-1].startswith("_param:salt_api_password"):
            _json["local"] = "fakepassword"
            return json.dumps(_json)

    return "emptyfakeresponse"
