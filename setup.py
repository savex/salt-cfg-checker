import glob
import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()

DATA = [
    ('etc', [f for f in glob.glob(os.path.join('etc', '*'))]),
    ('templates', [f for f in glob.glob(os.path.join('templates', '*'))]),
#    ('res', [f for f in glob.glob(os.path.join('res', '*'))])
]

dependencies = [
    'six',
    'pyyaml',
    'jinja2',
    'requests',
    'ipaddress'
]

entry_points = {
    "console_scripts":
        "mcp_checker = cfg_checker.cfg_check:cli_main"
}


setup(
    name="Mirantis Cloud Configuration Checker",
    version="0.1",
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
