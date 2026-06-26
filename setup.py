# setup.py
"""Setup script for Lumina."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="lumina",
    version="0.1.0",
    author="Lumina Project",
    description="A graphics scripting language compiler",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dipamsen/lumina",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "lumina=lumina.main:main",
        ],
    },
)