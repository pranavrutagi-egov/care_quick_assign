#!/usr/bin/env python

"""The setup script."""

from setuptools import find_packages, setup

with open("README.md") as readme_file:
    readme = readme_file.read()

with open("HISTORY.md") as history_file:
    history = history_file.read()

requirements = [
    "django",
    "celery",
    "djangorestframework",
]

test_requirements = []

setup(
    author="Open Healthcare Network",
    author_email="support@ohc.network",
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    description="Plugin to handle quick auto assignments for newly added patients",
    install_requires=requirements,
    license="MIT license",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="care_quick_assign",
    name="care_quick_assign",
    packages=find_packages(include=["care_quick_assign", "care_quick_assign.*"]),
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/ohcnetwork/care_quick_assign",
    version="0.1.0",
    zip_safe=False,
)
