"""
Setup file for Cookie Licking Detector CLI
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("VERSION", "r", encoding="utf-8") as fh:
    version = fh.read().strip()

setup(
    name="cookie-detector-cli",
    version=version,
    author="Cookie Licking Detector Team",
    author_email="support@cookie-detector.com",
    description="Command-line interface for the Cookie Licking Detector system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cookie-licking-detector/cli",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
        "rich>=10.0.0",
        "toml>=0.10.0",
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "cookie-detector=cookie_detector_cli:main",
        ],
    },
)