#!/usr/bin/env python3
"""
Setup script for ankityping plugin.

This provides a traditional Python package installation method
in addition to the custom package.py utility.
"""

from __future__ import annotations

from setuptools import setup, find_packages
import os
from pathlib import Path

# Read project metadata
project_root = Path(__file__).parent
src_dir = project_root / "src"

# Read README
readme_file = project_root / "README.md"
long_description = ""
if readme_file.exists():
    with open(readme_file, "r", encoding="utf-8") as f:
        long_description = f.read()

# Read version from pyproject.toml
version = "1.0.0"
pyproject_file = project_root / "pyproject.toml"
if pyproject_file.exists():
    with open(pyproject_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("version = "):
                version = line.split("=")[1].strip().strip('"\'')
                break

setup(
    name="ankityping",
    version=version,
    description="An Anki plugin for immersive typing practice",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="User",
    author_email="user@example.com",
    url="https://github.com/user/ankityping",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Plugins",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Education",
        "Topic :: Utilities",
    ],
    keywords="anki plugin typing practice language learning",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "PyQt6",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-qt>=4.0",
            "black>=22.0",
            "flake8>=4.0",
            "mypy>=0.900",
        ],
    },
    include_package_data=True,
    package_data={
        "ankityping": [
            "*.json",
            "*.md",
            "*.txt",
        ],
    },
    entry_points={
        "console_scripts": [
            "ankityping-package=ankityping.package:main",
        ],
    },
    zip_safe=False,
)