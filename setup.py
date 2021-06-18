# coding=utf-8

from setuptools import setup, find_packages
from io import StringIO, open
import fnmatch
from setuptools.command.build_py import build_py as build_py_orig
import os


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


excluded = ['pysimpledlna/win.py',
            'pysimpledlna/cli.py',
            'pysimpledlna/ac.py',
            'pysimpledlna/entity.py',
            'pysimpledlna/ui/*.py',
            'test/*.py']


def filter_py_file(item):
    print(item)
    return False


class build_py(build_py_orig):

    def find_package_modules(self, package, package_dir):
        modules = super().find_package_modules(package, package_dir)
        for (pkg, mod, file) in modules:
            print(f'custom build py {pkg} - {mod} - {file}')
        return [
            (pkg, mod, file)
            for (pkg, mod, file) in modules
            if not any(fnmatch.fnmatchcase(file, pat=os.path.normpath(pattern)) for pattern in excluded)
        ]

setup(
    name="pysimpledlna",
    version="0.5.1",
    author="wx c",
    description=("PySimpleDlna is a dlna server. It allows you to stream your videos to devices on your connected home network."),
    license="MIT",
    keywords="dlna",
    url="https://github.com/zqbxx/pysimpledlna",

    python_requires='>=3.8',

    install_requires=read_requirements('requirements.txt'),

    packages=find_packages(exclude=['pysimpledlna.ui', 'test']),
    cmdclass={'build_py': build_py},
    package_dir={'pysimpledlna': 'pysimpledlna'},
    package_data={'pysimpledlna': ['templates/*.xml']},

    long_description=read_README('README.md'),
    classifiers=[
        'Development Status :: 3 - Alpha',
        "Topic :: ",
        'Environment :: Console',
        'Intended Audience :: Developers',
        "License :: MIT",
        'Natural Language :: Chinese',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Multimedia :: Video',
    ],

    zip_safe=False
)
