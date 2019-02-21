from io import open

from setuptools import find_packages, setup

with open('cvpubsubs/__init__.py', 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.strip().split('=')[1].strip(' \'"')
            break
    else:
        version = '0.0.1'

with open('README.md', 'r', encoding='utf-8') as f:
    readme = f.read()

REQUIRES = [
    'opencv_python == 3.4.5.20',
    'localpubsub == 0.0.3',
    'numpy == 1.16.1'
]

setup(
    name='CVPubSubs',
    version=version,
    description='',
    long_description=readme,
    long_description_content_type='text/markdown',
    author='SimLeek',
    author_email='josh.miklos@gmail.com',
    maintainer='SimLeek',
    maintainer_email='josh.miklos@gmail.com',
    url='https://github.com/SimLeek/CV_PubSubs',
    license='MIT/Apache-2.0',

    keywords=[
        'opencv', 'camera',
    ],

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],

    install_requires=REQUIRES,
    tests_require=['coverage', 'pytest'],

    packages=find_packages(),
)
