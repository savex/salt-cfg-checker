import glob
import os

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()

DATA = [
    ('etc', [f for f in glob.glob(os.path.join('etc', '*'))]),
    ('templates', [f for f in glob.glob(os.path.join('templates', '*'))]),
    ('scripts', [f for f in glob.glob(os.path.join('scripts', '*'))]),
    ('versions', [f for f in glob.glob(os.path.join('versions', '*'))])
]

dependencies = [
    'six',
    'pyyaml',
    'jinja2',
    'requests',
    'ipaddress',
    'configparser'
]

entry_points = {
    "console_scripts": [
        "mcp-checker = cfg_checker.cfg_check:config_check_entrypoint",
        "mcp-pkg = cfg_checker.cli.packages:entrypoint",
        "mcp-net = cfg_checker.cli.network:entrypoint",
        "cmp-reclass = cfg_checker.cli.reclass:entrypoint"
    ]
}


setup(
    name="mcp-checker",
    version="0.41a",
    author="Alex Savatieiev",
    author_email="osavatieiev@mirantis.com",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7"
    ],
    keywords="QA, openstack, salt, config, reclass",
    entry_points=entry_points,
    url="",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        '': ['*.conf', '*.env', '*.list', '*.html']
    },
    zip_safe=False,
    install_requires=dependencies,
    data_files=DATA,
    license="Apache Licence, version 2",
    description="MCP Checker tool. For best results use on MCP deployments",
    long_description=README
)
