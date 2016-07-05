import os
from setuptools import setup, find_packages
from pip.req import parse_requirements

requirements_path = os.sep.join([os.path.dirname(os.path.abspath(__file__)), 'requirements.txt'])
install_reqs = parse_requirements(requirements_path, session=False)

reqs = [str(req) for req in install_reqs]

setup(
    name='traildb',
    version='0.0.1',
    description='TrailDB stores and queries cookie trails from raw logs.',
    author='AdRoll.com',
    packages=['traildb'],
    install_requires=reqs)
