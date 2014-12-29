import os
from setuptools import setup

HERE = os.path.dirname(__file__)

setup(
    name='xmodem',
    version='0.4.0',
    author='Wijnand Modderman, Jeff Quast',
    author_email='maze@pyth0n.org',
    description=('XMODEM protocol implementation.'),
    long_description = open(os.path.join(HERE, 'README.rst'), 'rb').read(),
    license='MIT',
    keywords='xmodem protocol',
    packages=['xmodem'],
    package_data={'': ['doc/*.TXT', 'doc/*.txt', 'README.rst']},
    include_package_data=True,
    data_files=[
        ('doc', ('doc/XMODEM.TXT',
                 'doc/XMODEM1K.TXT',
                 'doc/XMODMCRC.TXT',
                 'doc/ymodem.txt')),
    ],
)
