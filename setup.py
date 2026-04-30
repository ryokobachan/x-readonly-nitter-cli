from setuptools import setup, find_packages
import os
import re

# Read version from __init__.py
def get_version():
    init_path = os.path.join(os.path.dirname(__file__), "eneet", "__init__.py")
    with open(init_path, "r", encoding="utf-8") as f:
        content = f.read()
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
    raise RuntimeError("Unable to find version string.")

# Read long description from README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
def read_requirements(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return [
            line.strip()
            for line in f.readlines()
            if line.strip() and not line.startswith("#")
        ]

setup(
    name="eneet",
    version=get_version(),
    author="ryokobachan",
    author_email="fintics.org@gmail.com",
    description="Nitter API client for fetching tweets without Twitter API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ryokobachan/x-readonly-nitter-cli",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    keywords="twitter nitter api client scraper tweets social-media",
    python_requires=">=3.9",
    install_requires=read_requirements("requirements.txt"),
    project_urls={
        "Bug Reports": "https://github.com/ryokobachan/x-readonly-nitter-cli/issues",
        "Source": "https://github.com/ryokobachan/x-readonly-nitter-cli",
    },
    include_package_data=True,
    zip_safe=False,
)
