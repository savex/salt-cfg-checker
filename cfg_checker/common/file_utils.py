import grp
import os
import pwd
import time

from cfg_checker.common import config

_default_time_format = config.date_format


def remove_file(filename):
    os.remove(filename)
    # open('filename', 'w').close()


def write_str_to_file(filename, _str):
    with open(filename, 'w') as fo:
        fo.write(_str)


def append_str_to_file(filename, _str):
    with open(filename, 'a') as fa:
        fa.write(_str)


def write_lines_to_file(filename, source_list):
    with open(filename, 'w') as fw:
        fw.write("\n".join(source_list) + "\n")


def append_lines_to_file(filename, source_list):
    _buf = "\n".join(source_list)
    with open(filename, 'a') as fw:
        fw.write(_buf + "\n")


def append_line_to_file(filename, _str):
    with open(filename, 'a') as fa:
        fa.write(_str+'\n')


def read_file(filename):
    _buf = None
    with open(filename, 'rb') as fr:
        _buf = fr.read()
    return _buf


def read_file_as_lines(filename):
    _list = []
    with open(filename, 'rt') as fr:
        for line in fr:
            _list.append(line.rstrip())
    return _list


def get_file_info_fd(fd, time_format=_default_time_format):

    def format_time(unixtime):
        return time.strftime(
            time_format,
            time.gmtime(unixtime)
        )

    (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = \
        os.fstat(fd.fileno())

    _dict = {
        'fd': fd.fileno(),
        'mode': oct(mode & 0o777),
        'device': hex(dev),
        'inode': ino,
        'hard_links': nlink,
        'owner_id': uid,
        'owner_name': pwd.getpwuid(uid).pw_name,
        'owner_group_name': grp.getgrgid(gid).gr_name,
        'owner_group_id': gid,
        'size': size,
        'access_time': format_time(atime),
        'modification_time': format_time(mtime),
        'creation_time': format_time(ctime)
    }

    return _dict


def get_gzipped_file(url):
    # imports
    from io import BytesIO
    from requests import get
    import gzip
    # download a file
    _bytes = BytesIO(get(url).content)
    with gzip.GzipFile(fileobj=_bytes) as gz:
        return gz.read()


def ensure_folder_exists(_folder):
    if not os.path.exists(_folder):
        # it is not exists, create it
        os.mkdir(_folder)
        return "... folder '{}' created".format(_folder)
    else:
        return "... folder is at '{}'".format(_folder)


def ensure_folder_removed(_folder):
    if os.path.exists(_folder):
        os.rmdir(_folder)
        return "... folder '{}' removed".format(_folder)
    else:
        return "... folder '{}' not exists".format(_folder)
