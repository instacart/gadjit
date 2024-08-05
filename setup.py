from setuptools import setup, find_packages

setup(
    name="gadjit",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["boto3", "requests", "PyYAML"],
    entry_points={"console_scripts": ["gadjit=gadjit.__main__:main"]},
)
