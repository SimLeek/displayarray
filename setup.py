from distutils.core import setup
setup(
    name= 'cv_pubsubs',
    packages = ['cv_pubsubs', 'cv_pubsubs.webcam_pub', 'cv_pubsubs.window_sub'],
    version='0.1',
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
    ]
)