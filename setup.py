from setuptools import setup, find_packages

__version__ = "1.1.0"

setup(
    name="combo-e2e",
    version=__version__,
    description="Python end-to-end testing for Angular projects",
    url="https://github.com/AdCombo/combo-e2e",
    author="AdCombo Team",
    author_email="roman@adcombo.com",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="web e2e test testing end-to-end",
    packages=find_packages(exclude=["tests"]),
    zip_safe=False,
    platforms="any",
    install_requires=[
        "selenium==4.7.2",
        "requests==2.26.0",
        "lxml==4.9.2",
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    extras_require={"tests": "pytest"},
)
