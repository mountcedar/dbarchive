#!/usr/bin/env python
# -*- coding: utf-8 -*-

r'''
database archive feature for class instance
'''

__author__ = "Osamu Sugiyama"
__author_email__ = "sugiyama.o@gmail.com"
__date__ = "2016/1/2"
__version__ = "0.0.1b"

import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='dbarchive',
    version='0.0.1b',
    description='',
    author=__author__,
    author_email=__author_email__,
    url='',
    scripts=['src/dbarchive/dbarchive.py', ],
    package_dir={'': 'src'},
    packages=find_packages('src'),
    package_data={
        '': [
        ]
    },
    # namespace_packages=[''],
    long_description=__doc__,
    include_package_data=True,
    install_requires=[
        'click',
        'numpy',
        'scipy',
        'mongoengine'
    ],
    zip_safe=False
)
