#!/usr/bin/env python
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#
# @Author: oesteban - code@oscaresteban.es
# @Date:   2014-03-28 20:38:30
# @Last Modified by:   oesteban
# @Last Modified time: 2014-10-30 12:04:03

import os
import os.path as op

import nipype.pipeline.engine as pe             # pipeline engine
from nipype.interfaces import io as nio              # Data i/o
from nipype.interfaces import utility as niu         # utility

from pyacwereg.interfaces.acwereg import ACWEReg
from pyacwereg.interfaces.warps import FieldBasedWarp, InverseField


def regseg_wf(name='REGSEG'):
    wf = pe.Workflow(name=name)

    regseg_inputs = ['iterations', 'alpha', 'beta', 'step_size', 'grid_size',
                     'convergence_energy', 'convergence_window', 'f_smooth',
                     'images_verbosity']

    wf_inputs = ['in_fixed', 'in_tpms', 'in_surf', 'in_mask']
    inputnode = pe.Node(niu.IdentityInterface(
                        fields=regseg_inputs + wf_inputs), name='inputnode')

    outputnode = pe.Node(niu.IdentityInterface(
                         fields=['out_corr', 'out_tpms',
                                 'out_surf', 'out_field', 'out_mask']),
                         name='outputnode')

    enh = pe.MapNode(niu.Function(function=enh_image, input_names=['in_file'],
                                  output_names=['out_file']),
                     iterfield=['in_file'], name='Enhance')

    # Registration
    regseg = pe.Node(ACWEReg(), name="ACWERegistration")

    # Apply tfm to tpms
    applytfm = pe.MapNode(FieldBasedWarp(), name="ApplyWarp",
                          iterfield=['in_file'])

    # Connect
    wf.connect([
        (inputnode,   regseg, [(f, f) for f in regseg_inputs]),
        (inputnode,      enh, [('in_fixed', 'in_file')]),
        (enh,         regseg, [('out_file', 'in_fixed')]),
        (inputnode,   regseg, [('in_surf', 'in_prior')]),
        (inputnode, applytfm, [('in_tpms', 'in_file'),
                               ('in_mask', 'in_mask')]),
        (regseg,    applytfm, [('out_field', 'in_field')]),
        (regseg,  outputnode, [('out_warped', 'out_corr'),
                               ('out_field', 'out_field'),
                               ('out_surfs', 'out_surf')]),
        (applytfm, outputnode, [('out_file', 'out_tpms'),
                                ('out_mask', 'out_mask')])
    ])

    return wf


def default_regseg(name='REGSEGDefault'):
    wf = regseg_wf(name=name)

    # Registration
    # Good config for box phantom (2014/04/21): [ -a 0.0 -b 0.0 -u 20 -g 6 -i
    # 500 -s 1.0]
    wf.inputs.inputnode.iterations = [500, 500]
    # wf.inputs.inputnode.descript_update = [20]
    wf.inputs.inputnode.step_size = [1.0, .01]
    wf.inputs.inputnode.alpha = [0.0, 100.0]
    wf.inputs.inputnode.beta = [0.1, 1.]
    wf.inputs.inputnode.grid_size = [6, 8]
    wf.inputs.inputnode.convergence_energy = [True] * 2
    wf.inputs.inputnode.convergence_window = [50, 25]
    wf.inputs.inputnode.f_smooth = [2.0, None]
    wf.inputs.inputnode.images_verbosity = 3
    return wf


def identity_wf(name='Identity', n_tissues=3):
    """
    An identity workflow to check how ideal inverse transform
    affects final evaluation scores.
    """
    wf = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(
                        fields=['in_fixed', 'in_tpms', 'in_surf',
                                'in_mask', 'in_field', 'grid_size']),
                        name='inputnode')

    outputnode = pe.Node(niu.IdentityInterface(
                         fields=['out_corr', 'out_tpms',
                                 'out_surf', 'out_field', 'out_mask']),
                         name='outputnode')

    # Invert field
    inv = pe.Node(InverseField(), name='InvertField')

    # Compute corrected images
    merge = pe.Node(niu.Merge(2), name='Merge')
    split = pe.Node(niu.Split(splits=[2, n_tissues]), name='Split')

    # Apply tfm to tpms
    applytfm = pe.Node(FieldBasedWarp(), name="ApplyWarp")

    # Connect
    wf.connect([
        (inputnode,       inv, [('in_field', 'in_field')]),
        (inputnode,     merge, [('in_fixed', 'in1'),
                                ('in_tpms', 'in2')]),
        (inputnode,  applytfm, [('in_mask', 'in_mask'),
                                ('in_surf', 'in_surf'),
                                ('grid_size', 'grid_size')]),
        (merge,      applytfm, [('out', 'in_file')]),
        # (inputnode,  applytfm, [('in_field', 'in_field')]),
        (inv,        applytfm, [('out_field', 'in_field')]),
        (applytfm,      split, [('out_file', 'inlist')]),
        (split,    outputnode, [('out1', 'out_corr'),
                                ('out2', 'out_tpms')]),
        (inv,      outputnode, [('out_field', 'out_field')]),
        (applytfm, outputnode, [('out_surf', 'out_surf'),
                                ('out_mask', 'out_mask')])
    ])

    return wf


def enh_image(in_file, irange=2000., out_file=None):
    import numpy as np
    import nibabel as nb
    import os.path as op

    if out_file is None:
        fname, fext = op.splitext(op.basename(in_file))
        if fext == '.gz':
            fname, _ = op.splitext(fname)
        out_file = op.abspath('./%s_enh.nii.gz' % fname)

    nii = nb.load(in_file)
    data = nii.get_data()
    data[data < 0] = 0.0
    imax = data.max()
    data = (irange / imax) * data

    nb.Nifti1Image(data, nii.get_affine(), nii.get_header()).to_filename(
        out_file)
    return out_file
