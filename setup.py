# coding=utf-8

from setuptools import setup

setup(
    name="pysimpledlna",  #pypi中的名称，pip或者easy_install安装时使用的名称
    version="0.0.1",
    author="wx c",
    description=("PySimpleDlna is a dlna server. It allows you to stream your videos to devices on your connected home network."),
    license="MIT",
    keywords="dlna",
    url="",

    # 需要安装的依赖
    install_requires=[
        'twisted>=16.2.0','lxml'
    ],

    entry_points={
        'console_scripts': [
            'pysimpledlna = pysimpledlna.cli:main',
        ]
    },

    packages=['pysimpledlna'],
    package_dir={'pysimpledlna': 'pysimpledlna'},
    package_data={'pysimpledlna': ['templates/*.xml']},

    #long_description=read('README.md'),
    classifiers=[  # 程序的所属分类列表
        'Development Status :: 3 - Alpha',
        "Topic :: ",
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        "License :: MIT",
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Video',
        'Topic :: Utilities'
    ],

    zip_safe=False
)