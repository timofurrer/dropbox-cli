#!/usr/bin/python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name="dropbox-cli",
    version="0.00.01",
    description="cli to manage your dropbox account ",
    author="Timo Furrer",
    author_email="tuxtimo@gmail.com",
    url="http://github.com/timofurrer/dropbox-cli",
    packages=["dbc"],
    install_requires=["clicore==0.00.01", "dropbox==1.5.1"],
    entry_points={"console_scripts": ["dbc = dbc.main:main"]},
    package_data={"dbc": ["*.md"]}
)
