#!/usr/bin/python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name="dbc",
    version="0.00.01",
    description="cli to manage your dropbox account ",
    author="Timo Furrer",
    author_email="tuxtimo@gmail.com",
    url="http://github.com/timofurrer/dropbox-cli",
    packages=["dbc"],
    entry_points={"console_scripts": ["dbc = dbc.main:main"]},
    package_data={"dbc": ["*.md"]}
)
