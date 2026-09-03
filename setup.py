#!/usr/bin/env python3
"""
Setup configuration for DR Setup Guide
Disaster Recovery automation for Confluent Cloud and Kafka Connect on AWS EKS
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="dr-setup-guide",
    version="1.0.0",
    description="Comprehensive guide for Disaster Recovery (DR) setup using Confluent Cloud and Kafka Connect on AWS EKS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="ssenapathy-wam",
    author_email="",
    url="https://github.com/ssenapathy-wam/dr-setup-guide",
    license="MIT",
    python_requires=">=3.8",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "confluent-kafka>=2.3.0",
        "kafka-python>=2.0.2",
        "pyyaml>=6.0.1",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "boto3>=1.28.85",
        "kubernetes>=28.1.0",
        "click>=8.1.7",
        "rich>=13.7.0",
        "tabulate>=0.9.0",
        "tenacity>=8.2.3",
        "paramiko>=3.4.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "black>=23.12.0",
            "flake8>=6.1.0",
            "pylint>=3.0.3",
            "mypy>=1.7.1",
        ],
        "docs": [
            "sphinx>=7.2.6",
            "sphinx-rtd-theme>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "dr-setup=dr_orchestrator:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Distributed Computing",
    ],
    keywords="disaster-recovery kafka confluent aws eks",
    project_urls={
        "Bug Reports": "https://github.com/ssenapathy-wam/dr-setup-guide/issues",
        "Source": "https://github.com/ssenapathy-wam/dr-setup-guide",
    },
)
