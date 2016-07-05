from setuptools import setup, find_packages

setup(
    name='traildb',
    version='0.0.1',
    description='TrailDB stores and queries cookie trails from raw logs.',
    author='AdRoll.com',
    packages=find_packages(),
    install_requires=[
        'future==0.15.2',
        'nose2==0.5.0'
    ])
