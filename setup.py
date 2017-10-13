#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: oesteban
# @Date:   2015-11-19 16:44:27
# @Last Modified by:   oesteban
# @Last Modified time: 2017-10-13 15:08:22
""" regseg setup script """
from __future__ import print_function, division, absolute_import, unicode_literals


def main():
    """ Install entry-point """
    from sys import version_info
    from setuptools import setup, find_packages
    from regseg.__about__ import (
        __version__,
        __author__,
        __email__,
        __license__,
        __description__,
        __longdesc__,
        __url__,
        __download__,
        PACKAGE_NAME,
        CLASSIFIERS,
        REQUIRES,
        SETUP_REQUIRES,
        LINKS_REQUIRES,
        TESTS_REQUIRES,
        EXTRA_REQUIRES,
    )

    package_data = {'regseg': ['data/*.json', 'data/*.txt']}
    if version_info[0] < 3:
        package_data = {key.encode(): [v.encode() for v in val]
                        for key, val in list(package_data.items())}

    setup(
        name=PACKAGE_NAME,
        version=__version__,
        description=__description__,
        long_description=__longdesc__,
        author=__author__,
        author_email=__email__,
        license=__license__,
        maintainer_email=__email__,
        classifiers=CLASSIFIERS,
        # Dependencies handling
        setup_requires=SETUP_REQUIRES,
        install_requires=REQUIRES,
        dependency_links=LINKS_REQUIRES,
        tests_require=TESTS_REQUIRES,
        extras_require=EXTRA_REQUIRES,
        url=__url__,
        download_url=__download__,
        packages=find_packages(exclude=['*.tests']),
        package_data=package_data,
        entry_points={
            'console_scripts': [],  # format 'mriqc=mriqc.bin.mriqc_run:main'
        },
        scripts=[
            'tools/extract_hcp.py',
            'tools/run_evaluations.py',
            'tools/run_phantoms.py'
        ],
        zip_safe=False
    )


if __name__ == "__main__":
    main()
