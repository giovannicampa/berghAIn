from setuptools import setup, find_packages

with open("README.md", "r") as f:
    long_description = f.read()

with open('requirements.txt', "r") as f:
    requirements = f.read().splitlines()

setup(
    name="berghAIn",
    version="0.1.0",
    description="Predict the length of the queue at Beghain with ML",
    long_description=long_description,
    author="Giovanni Campa",
    author_email="giocampa93@gmail.com",
    packages=find_packages(),
    install_requires=requirements,
    extras_require={
        "dev": [
            "pre-commit==3.3.3",
        ]
    }
)