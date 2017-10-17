#!/usr/bin/env python
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
Python wrapper to RegSeg
========================

"""
from __future__ import print_function, division, absolute_import, unicode_literals
from datetime import date

__version__ = '0.1.0'
__author__ = 'Oscar Esteban'
__email__ = 'code@oscaresteban.es'
__maintainer__ = 'Oscar Esteban'
__copyright__ = 'Copyright 2017-%d, Oscar Esteban' % date.today().year
__credits__ = 'Oscar Esteban'
__license__ = 'MIT License'
__status__ = 'Alpha'
__description__ = """\
Python interface to RegSeg, a surface-driven registration method \
for the structure-informed segmentation of multispectral brain images\
"""

__longdesc__ = """\
RegSeg is a simultaneous segmentation and registration method that \
uses active contours without edges (ACWE) extracted from structural \
images. The contours evolve through a free-form deformation field \
supported by the B-spline basis to optimally map the contours onto \
the data in the target space.\
"""

__url__ = 'http://pyregseg.readthedocs.org/'
__download__ = ('https://github.com/oesteban/pyregseg/archive/'
                '{}.tar.gz'.format(__version__))

PACKAGE_NAME = 'regseg'
CLASSIFIERS = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Science/Research',
    'Topic :: Scientific/Engineering :: Image Recognition',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
]

SETUP_REQUIRES = []

REQUIRES = [
    'numpy>=1.12.0',
    'matplotlib',
    'nibabel',
    'pandas',
    'dipy',
    'seaborn',
    'nipype',
    'phantomas',
    'nilearn',
    'niworkflows',
]

LINKS_REQUIRES = [
    'git+https://github.com/oesteban/nipype.git@'
    'a24db85b85ff8b60fa3bb561f617e45e534cb5aa#egg=nipype-0.13.2',
    'git+https://github.com/oesteban/phantomas.git@'
    '1f512c770a44f10192ed3bb6b5772f4984627474#egg=phantomas-1.0.0',
]


TESTS_REQUIRES = [
    # 'mock',
    # 'codecov',
    'pytest-xdist'
]

EXTRA_REQUIRES = {
    'doc': ['sphinx>=1.5,<1.6', 'sphinx_rtd_theme>=0.2.4', 'sphinx-argparse'],
    'tests': TESTS_REQUIRES,
    # 'duecredit': ['duecredit'],
    'notebooks': ['ipython', 'jupyter'],
}

# Enable a handle to install all extra dependencies at once
EXTRA_REQUIRES['all'] = [val for _, val in list(EXTRA_REQUIRES.items())]
