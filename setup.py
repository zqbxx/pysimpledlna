# coding=utf-8

from setuptools import setup, find_packages
from io import StringIO, open


def read_file(filename):
    with open(filename, 'r', encoding='UTF-8') as fp:
        return fp.read().strip()


def read_requirements(filename):
    return [line.strip() for line in read_file(filename).splitlines()
            if not line.startswith('#')]


def read_README(filename):
    # Ignore unsupported directives by pypi.
    content = read_file(filename)
    return ''.join(line for line in StringIO(content)
                   if not line.startswith('.. comment::'))


setup(
    name="pysimpledlna",
    version="0.3.0",
    author="wx c",
    description=("PySimpleDlna is a dlna server. It allows you to stream your videos to devices on your connected home network."),
    license="MIT",
    keywords="dlna",
    url="https://github.com/zqbxx/pysimpledlna",

    python_requires='>=3.7',

    install_requires=read_requirements('requirements.txt'),

    entry_points={
        'console_scripts': [
            'pysimpledlna = pysimpledlna.cli:main',
            'pysimpledlnaW = pysimpledlna.win:main',
        ]
    },

    packages=find_packages(),
    package_dir={'pysimpledlna': 'pysimpledlna'},
    package_data={'pysimpledlna': ['templates/*.xml']},

    long_description=read_README('README.md'),
    classifiers=[
        'Development Status :: 3 - Alpha',
        "Topic :: ",
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        "License :: MIT",
        'Natural Language :: Chinese',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Video',
        'Topic :: Utilities'
    ],

    zip_safe=False
)
