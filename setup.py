import os
import codecs
from setuptools import setup

HERE = os.path.dirname(__file__)
README_RST = os.path.join(HERE, 'README.rst')

setup(
    name='xmodem',
    version='0.4.6',
    author='Wijnand Modderman, Jeff Quast, Kris Hardy',
    author_email='maze@pyth0n.org',
    description=('XMODEM protocol implementation.'),
    url='https://github.com/tehmaze/xmodem',
    long_description = codecs.open(README_RST, 'rb', 'utf8').read(),
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
