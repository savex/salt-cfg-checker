"""
Base configuration module
Gathers env values and supplies default ones

Attributes:
    base_config: class with all of the values prepared to work with env
"""

import os

from check_versions.common.other import utils

PKG_DIR = os.path.dirname(__file__)
PKG_DIR = os.path.join(PKG_DIR, os.pardir, os.pardir)
PKG_DIR = os.path.normpath(PKG_DIR)

_default_work_folder = os.path.normpath(PKG_DIR)


class TestsConfigurationBase(object):
    """
    Base configuration class. Only values that are common for all scripts
    """

    name = "CiTestsBaseConfig"
    logfile_name = 'ci_packages.log'
    working_folder = os.environ.get('CI_TESTS_WORK_DIR', _default_work_folder)
    salt_host = os.environ.get('SALT_URL', None)
    salt_port = os.environ.get('SALT_PORT', '6969')
    salt_user = os.environ.get('SALT_USER', 'salt')
    salt_pass = os.environ.get('SALT_PASSWORD', None)

    salt_timeout = os.environ.get('SALT_TIMEOUT', 30)
    salt_file_root = os.environ.get('SALT_FILE_ROOT', None)
    salt_scripts_folder = os.environ.get('SALT_SCRIPTS_FOLDER', 'test_scripts')

    all_nodes = utils.get_nodes_list(
        os.environ.get('CI_ALL_NODES', None),
        os.environ.get('SALT_NODE_LIST_FILE', None)
    )
    skip_nodes = utils.node_string_to_list(os.environ.get(
        'CI_SKIP_NODES',
        None
    ))


base_config = TestsConfigurationBase()
