#!/usr/bin/env python

from distutils.core import setup

pkgs = (["semanticizer"] +
        ["semanticizer." + sub for sub in ("processors", "redisinsert",
                                           "server", "util", "wpm")])

setup(
    name="semanticizer",
    description="Entity Linking for the masses",
    packages=pkgs,
    classifiers=[
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Text Processing",
    ],
    install_requires=[
        "flask",
        "joblib",
        "mock",
        "lxml",
        "networkx",
        "numpy",
        "python-Levenshtein",
        "scikit-learn",
        "simplejson",
    ],
)
