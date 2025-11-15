from setuptools import setup, find_packages

setup(
    name="hdlproto",
    version="0.2.0",
    author="shntn",
    author_email="qzt112222@nifty.com",
    description="A Python-based HDL design prototyping framework for circuit simulation and verification",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/shntn/hdlproto",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=[
    ],
)