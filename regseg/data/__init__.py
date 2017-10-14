#!/usr/bin/env python
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#
# @Author: oesteban - code@oscaresteban.es
# @Date:   2014-06-03 11:49:42
# @Last Modified by:   oesteban
# @Last Modified time: 2017-10-13 14:55:28
"""Complementary data necessary in workflows

.. module:: regseg.data
   :synopsis: data required by :py:mod:`regseg`

.. moduleauthor:: Oscar Esteban <code@oscaresteban>

"""
from __future__ import print_function, division, absolute_import, unicode_literals
from pkg_resources import resource_filename as pkgrf

folders = {
    't2b_params': {i: pkgrf('regseg', 'data/t2b_elastix_%s.txt' % i)
                   for i in ['x', 'y', 'z']},
    'regseg_hcp': pkgrf('regseg', 'data/regseg_hcp.json'),
    'regseg_default': pkgrf('regseg', 'data/regseg_default.json'),
    'model_labels': pkgrf('regseg', 'data/model_labels.json'),
}

def get(value):
    """Get a particular data resource"""
    if value not in folders:
        raise RuntimeError('Requested data resource "%s" does not exist' % value)
    else:
        return folders[value]

