# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
Workflows to handle BOLD data
"""
from __future__ import print_function, division, absolute_import, unicode_literals
import nipype.pipeline.engine as pe
from .surfaces import extract_surface


def bold_sdc_regseg(name='bold_regseg'):
    """
    A regseg-based :abbr:`SDC (susceptibility distortion correction)` workflow
    for :abbr:`BOLD (blood-oxygen-level dependent)` MRI.

    """

    wf = pe.Workflow(name=name)

    return wf



def bold_model_surfaces(name='bold_surfaces', gen_outer=False):
    from nipype.interfaces.io import JSONFileGrabber
    from .. import data

    inputnode = pe.Node(niu.IdentityInterface(
        fields=['aseg', 'norm', 'in_mask']), name='inputnode')
    outputnode = pe.Node(niu.IdentityInterface(
        fields=['out_surf']), name='outputnode')

    readls = pe.Node(JSONFileGrabber(in_file=data.get('model_labels')),
                     name='ReadModelLabels')

    nsurfs = 0
    tha = extract_surface(name='ThalSurface')
    tha.inputs.inputnode.name = '%02d.thalamus' % nsurfs
    nsurfs += 1

    csf = extract_surface(name='VdGMSurface')
    csf.inputs.inputnode.name = '%02d.csf_dgm' % nsurfs
    nsurfs += 1

    bstem = extract_surface(name='stemSurface')
    bstem.inputs.inputnode.name = '%02d.bstem' % nsurfs
    nsurfs += 1

    wm = extract_surface(name='WMSurface')
    wm.inputs.inputnode.name = '%02d.white' % nsurfs
    nsurfs += 1

    cgm = extract_surface(name='cbGMSurface')
    cgm.inputs.inputnode.name = '%02d.cgm' % nsurfs
    nsurfs += 1

    pial = extract_surface(name='PialSurface')
    pial.inputs.inputnode.name = '%02d.pial' % nsurfs
    nsurfs += 1

    if gen_outer:
        nsurfs = nsurfs + 1

    m = pe.Node(niu.Merge(nsurfs), name='MergeSurfs')

    wf = pe.Workflow(name=name)
    wf.connect([
        (inputnode, tha,   [('aseg', 'inputnode.aseg'),
                            ('norm', 'inputnode.norm')]),
        (readls,    tha,   [('thal_labels', 'inputnode.labels')]),
        (tha,       m,     [('outputnode.out_surf', 'in1')]),
        (inputnode, csf,   [('aseg', 'inputnode.aseg'),
                            ('norm', 'inputnode.norm')]),
        (readls,    csf,   [('csf_dgm_labels', 'inputnode.labels')]),
        (csf,       m,     [('outputnode.out_surf', 'in2')]),
        (inputnode, bstem, [('aseg', 'inputnode.aseg'),
                            ('norm', 'inputnode.norm')]),
        (readls,    bstem, [('bstem_labels', 'inputnode.labels')]),
        (bstem,     m,     [('outputnode.out_surf', 'in3')]),
        (inputnode, wm,    [('aseg', 'inputnode.aseg'),
                            ('norm', 'inputnode.norm')]),
        (readls,    wm,    [('wm_labels', 'inputnode.labels')]),
        (wm,        m,     [('outputnode.out_surf', 'in4')]),
        (inputnode, cgm,   [('aseg', 'inputnode.aseg'),
                            ('norm', 'inputnode.norm')]),
        (readls,    cgm,   [('cgm_labels', 'inputnode.labels')]),
        (cgm,       m,     [('outputnode.out_surf', 'in5')]),
        (inputnode, pial,  [('aseg', 'inputnode.aseg'),
                            ('norm', 'inputnode.norm')]),
        (readls,    pial,  [('gm_labels', 'inputnode.labels')]),
        (pial,      m,     [('outputnode.out_surf', 'in6')]),
        (m,    outputnode, [('out', 'out_surf')])
    ])

    if gen_outer:
        msk = extract_surface(name='MaskSurf')
        msk.inputs.inputnode.labels = [1]
        msk.inputs.inputnode.name = '%01d.outer' % nsurfs - 1

        wf.connect([
            (inputnode, msk,  [('in_mask', 'inputnode.aseg'),
                               ('in_mask', 'inputnode.norm')]),
            (msk,       m,    [('outputnode.out_surf', 'in%d' % nsurfs)])
        ])
    return wf
