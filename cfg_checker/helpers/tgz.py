import os
import tarfile as tarfile
import tempfile

from cfg_checker.common import logger_cli
from cfg_checker.common.exception import ConfigException


class TGZFile(object):
    basefile = None
    _labelname = "labelfile"

    def __init__(self, _filepath, label=None):
        # Check if this filename exists
        if not os.path.exists(_filepath):
            # If the archive not exists, create it
            # simple labelfile for a non-empty archive

            if not label:
                label = "MCP Checker TGZ file"

            with tempfile.TemporaryFile() as _tempfile:
                _tempfile.write(label.encode('utf-8'))
                _tempfile.flush()
                _tempfile.seek(0)
                # create tgz
                with tarfile.open(_filepath, "w:gz") as tgz:
                    _info = tgz.gettarinfo(
                        arcname=self._labelname,
                        fileobj=_tempfile
                    )
                    tgz.addfile(_info, fileobj=_tempfile)
                logger_cli.debug("... created file '{}'".format(_filepath))
                self.basefile = _filepath

        elif not os.path.isfile(_filepath):
            # if path exists, and it is not a file
            raise ConfigException(
                "Supplied path of '{}' is not a file".format(
                    _filepath
                )
            )
        elif not tarfile.is_tarfile(_filepath):
            # if file exists, and it is not a tar file
            raise ConfigException(
                "Supplied file of '{}' is not a TAR stream".format(
                    _filepath
                )
            )
        else:
            self.basefile = _filepath

    def get_file(self, name, decode=False):
        if self.has_file(name):
            with tarfile.open(self.basefile, "r:gz") as tgz:
                _tgzitem = tgz.extractfile(tgz.getmember(name))
                if decode:
                    return _tgzitem.read().decode('utf-8') 
                else:
                    return _tgzitem.read()
        else:
            return None

    def add_file(self, name, buf=None, replace=False):
        _files = []
        with tarfile.open(self.basefile) as r:
            _files = r.getnames()
            _exists = name in _files
            if _exists and not replace:
                # file exists and replace flag is not set
                return False

        # check if there is work to do
        if not buf and not os.path.exists(name):
            # Nothing to do: no buffer or file to add
            return False
        elif name in self.list_files() and not replace:
            # file already there and replace flag not set
            return False

        _a = "replace" if replace else "add"
        logger_cli.debug("... about to {} '{}' ({:.2f}MB) -> '{}'".format(
            _a,
            name,
            float(len(buf))/1024/1024,
            self.basefile
        ))

        # unzip tar, add file, zip it back
        _tmpdir = tempfile.mkdtemp()
        logger_cli.debug("... created tempdir '{}'".format(_tmpdir))
        # extract them
        _files = []
        with tarfile.open(self.basefile) as r:
            # all names extracted
            _files = r.getnames()
            # extract 'em
            logger_cli.debug("... extracting contents")
            r.extractall(_tmpdir)

        # create file
        if buf:
            _p = os.path.join(_tmpdir, name)
            logger_cli.debug("... writing new file to '{}'".format(
                _p
            ))
            if not _exists or replace:
                with open(_p, "w") as w:
                    w.write(buf)
            if not _exists:
                _files.append(name)
        # create the archive
        logger_cli.debug("... rebuilding archive")
        with tarfile.open(self.basefile, "w:gz") as tgz:
            for _file in _files:
                _p = os.path.join(_tmpdir, _file)
                tgz.add(_p, arcname=_file)
                os.remove(_p)
        os.rmdir(_tmpdir)
        return True

    def list_files(self):
        # get names
        with tarfile.open(self.basefile, "r:gz") as tgz:
            _names = tgz.getnames()
        # filter filenames only, skip path
        if any(['/' in _n for _n in _names]):
            _n = []
            for f in _names:
                if '/' in f:
                    _n.append(f.rsplit('/', 1)[1])
                else:
                    _n.append(f)
            _names = _n
        # remove label file from output
        if self._labelname in _names:
            _names.remove(self._labelname)
        return _names

    def has_file(self, name):
        if name in self.list_files():
            logger_cli.debug("... '{}' has '{}'".format(self.basefile, name))
            return True
        else:
            logger_cli.debug("... '{}' lacks '{}'".format(self.basefile, name))
            return False
