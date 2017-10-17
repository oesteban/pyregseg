# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
Workflows to handle BOLD data
"""
from __future__ import print_function, division, absolute_import, unicode_literals
from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces.ants import ApplyTransforms

from .. import data
from ..interfaces.niworkflows import GenerateSamplingReference
from .surfaces import extract_surfaces_model
from .registration import regseg_wf

def bold_sdc_regseg(name='bold_regseg'):
    """
    A regseg-based :abbr:`SDC (susceptibility distortion correction)` workflow
    for :abbr:`BOLD (blood-oxygen-level dependent)` MRI.

    """

    inputnode = pe.Node(
        niu.IdentityInterface(['t1_brain', 't1_mask', 't1_aseg', 'bold_ref',
                               'itk_t1_to_bold']),
        name='inputnode')

    # 1. Resample the T1w, the brainmask and the parcellation in BOLD space,
    #    BUT keeping the original high resolution of the T1w image.
    ref_bold = pe.Node(GenerateSamplingReference(), name='T1toBOLDSamplingReference')

    t1brain_bold = pe.Node(ApplyTransforms(), name='T1toBOLD')

    t1mask_bold = pe.Node(ApplyTransforms(interpolation='NearestNeighbor', float=True),
                          name='T1toBOLDMask')
    # TODO
    # mri_label2vol --seg mri/aparc+aseg.mgz --temp mri/rawavg.mgz --o ~/tmp/regseg/bold/aparc.nii.gz --regheader mri/aparc+aseg.mgz
    t1aseg_bold = pe.Node(ApplyTransforms(interpolation='NearestNeighbor', float=True),
                          name='T1toBOLDAseg')

    # 2. Reconstruct the model surfaces on BOLD space
    exsurfs = extract_surfaces_model('model_bold_labels')

    wf = pe.Workflow(name=name)
    wf.connect([
        (inputnode, ref_bold, [('bold_ref', 'fixed_image'),
                               ('t1_brain', 'moving_image')]),
        (inputnode, t1brain_bold, [('t1_brain', 'input_image'),
                                   ('itk_t1_to_bold', 'transforms')]),
        (inputnode, t1mask_bold, [('t1_mask', 'input_image'),
                                  ('itk_t1_to_bold', 'transforms')]),
        (inputnode, t1aseg_bold, [('t1_aseg', 'input_image'),
                                  ('itk_t1_to_bold', 'transforms')]),
        (ref_bold, t1brain_bold, [('out_file', 'reference_image')]),
        (ref_bold, t1mask_bold, [('out_file', 'reference_image')]),
        (ref_bold, t1aseg_bold, [('out_file', 'reference_image')]),
        (t1brain_bold, exsurfs, [('output_image', 'inputnode.norm')]),
        (t1mask_bold, exsurfs, [('output_image', 'inputnode.in_mask')]),
        (t1aseg_bold, exsurfs, [('output_image', 'inputnode.aseg')]),
    ])

    # 3. Run regseg
    regseg = regseg_wf(data.get('regseg_hcp'), usemask=False, enhance_inputs=False)

    wf.connect([
        (inputnode, regseg, [('bold_ref', 'inputnode.in_fixed')]),
        (exsurfs, regseg, [('outputnode.out_surf', 'inputnode.in_surf')]),
    ])

    return wf
