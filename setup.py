#!/usr/bin/env python3
"""Setup script for scullery."""

import os
from setuptools import find_packages, setup

# Import __meta__ without triggering the full package
import importlib.util
_meta_path = os.path.join(os.path.dirname(__file__), "scullery", "__meta__.py")
_spec = importlib.util.spec_from_file_location("__meta__", _meta_path)
_meta = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_meta)

with open(os.path.join(os.path.dirname(__file__), "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name=_meta.name,
    version=_meta.version,
    author=_meta.author,
    author_email=_meta.author_email,
    description=_meta.description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=_meta.url,
    license=_meta.license,
    packages=find_packages(exclude=["docs", "docs.*", "scripts", "examples"]),
    python_requires=">=3.9",
    install_requires=[
        "pyyaml",
        "requests",
        "questionary",
        "ruamel.yaml",
        "configupdater",
        "mypielib @ git+https://github.com/TortugaLabs/mypielib.git@main",
        "tcurl @ git+https://github.com/aliuly/tcurl.git@main",
    ],
    extras_require={
        "icecream": ["icecream"],
        "dev": [
            "ruff",
            "py-cyclo",
            "detect-secrets",
        ],
    },
    entry_points={
        "console_scripts": [
            "scullery=scullery.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    project_urls={
        "Bug Tracker": "https://github.com/aliuly/scullery/issues",
        "Source": "https://github.com/aliuly/scullery",
    },
)
