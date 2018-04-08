from distutils.core import setup
from setuptools import find_packages

setup(
    name= 'cv_pubsubs',
    version='1.0.0',
    packages = find_packages(),
    description='Pubsub interface for Python OpenCV',
    author='Josh Miklos',
    author_email='simulatorleek@gmail.com',
    url='https://github.com/SimLeek/cv_pubsubs',
    download_url='https://github.com/SimLeek/cv_pubsubs/archive/0.1.tar.gz',
    keywords=['OpenCV', 'PubSub'],
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ]
)