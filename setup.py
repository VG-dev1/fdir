from setuptools import setup
import pathlib

HERE = pathlib.Path(__file__).parent

README = (HERE / "README.md").read_text()

setup(
    name="fdir-cli",
    version="3.3.0",
    description="Find and organize anything on your system",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/VG-dev1/fdir",
    author="VG-dev1",
    author_email="vitohackergrgic@gmail.com",
    license="MIT",
    classifiers=[

        "Development Status :: 5 - Production/Stable",

        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",

        "License :: OSI Approved :: MIT License",

        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    keywords="search, cli, terminal, command-line, tool, filesystem",
    py_modules=["fdir"],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "fdir = fdir:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/VG-dev1/fdir/issues",
        "Source": "https://github.com/VG-dev1/fdir",
    },
)