from setuptools import setup, find_packages

__version__ = "1.0.0"

setup(
    name="combo-e2e",
    version=__version__,
    description="Python end-to-end testing for AngularJS projects",
    url="https://github.com/AdCombo/combo-e2e",
    author="AdCombo Team",
    author_email="roman@adcombo.com",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="web e2e test testing end-to-end",
    packages=find_packages(exclude=["tests"]),
    zip_safe=False,
    platforms="any",
    install_requires=[
        'selenium==3.11.0',
        'requests==2.23.0',
        'lxml>=3.6.0',
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    extras_require={"tests": "pytest"},
)
