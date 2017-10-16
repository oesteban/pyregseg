# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
Surface extraction
++++++++++++++++++

Defines the workflows for extracting surfaces from segmentations

:platform: Unix
:moduleauthor: Oscar Esteban <code@oscaresteban>

"""
from __future__ import print_function, division, absolute_import, unicode_literals
from sys import version_info
import nipype.pipeline.engine as pe             # pipeline engine
from nipype.interfaces import utility as niu    # utility
from nipype.interfaces import freesurfer as fs  # Freesurfer
from ..interfaces.nilearn import Binarize
from ..interfaces.surfaces import FixVTK

PY2 = version_info[0] < 3


def extract_surface(name='GenSurface'):
    """ A nipype workflow for surface extraction from ``labels`` in a segmentation.

    .. note :: References used to implement this code:

      * <https://github.com/nipy/nipype/issues/307>
      * <https://mail.nmr.mgh.harvard.edu/pipermail/\
freesurfer/2011-November/021391.html>
      * <http://brainder.org/2012/05/08/importing-\
freesurfer-subcortical-structures-into-blender/>
      * <https://mail.nmr.mgh.harvard.edu/pipermail/\
freesurfer/2013-June/030586.html>
    """
    inputnode = pe.Node(niu.IdentityInterface(
        fields=['aseg', 'norm', 'in_filled', 'labels', 'name'],
        mandatory_inputs=False),
        name='inputnode')
    outputnode = pe.Node(niu.IdentityInterface(
        fields=['out_surf', 'out_binary']), name='outputnode')
    binarize = pe.Node(Binarize(), name='BinarizeLabels')
    fill = pe.Node(niu.Function(
        function=_fillmask, input_names=['in_file', 'in_filled'],
        output_names=['out_file']), name='FillMask')
    pretess = pe.Node(fs.MRIPretess(label=1), name='PreTess')
    tess = pe.Node(fs.MRITessellate(label_value=1), name='tess')
    smooth = pe.Node(fs.SmoothTessellation(disable_estimates=True),
                     name='mris_smooth')
    rename = pe.Node(niu.Rename(keep_ext=False),
                     name='rename')

    tovtk = pe.Node(fs.MRIsConvert(out_datatype='vtk'), name='toVTK')
    fixVTK = pe.Node(FixVTK(), name='fixVTK')

    wf = pe.Workflow(name=name)
    wf.connect([
        (inputnode,   binarize,   [('aseg', 'in_file'),
                                   ('labels', 'match')]),
        (inputnode,   fixVTK,     [('norm', 'in_ref')]),
        (inputnode,   pretess,    [('norm', 'in_norm')]),
        (inputnode,   fill,       [('in_filled', 'in_filled')]),
        (binarize,    fill,       [('out_file', 'in_file')]),
        (fill,        pretess,    [('out_file', 'in_filled')]),
        (pretess,     tess,       [('out_file', 'in_file')]),
        (tess,        smooth,     [('surface', 'in_file')]),
        (smooth,      rename,     [('surface', 'in_file')]),
        (inputnode,   rename,     [('name', 'format_string')]),
        (rename,      tovtk,      [('out_file', 'in_file')]),
        (tovtk,       fixVTK,     [('converted', 'in_file')]),
        (fixVTK,      outputnode, [('out_file', 'out_surf')]),
        (fill,        outputnode, [('out_file', 'out_binary')])
    ])
    return wf


def extract_surfaces_model(model, name='Surfaces', gen_outer=False):
    """Extracts surfaces as prescribed by the model ``model``"""
    import simplejson as json
    from .. import data
    from pkg_resources import resource_filename as pkgrf

    inputnode = pe.Node(niu.IdentityInterface(
        fields=['aseg', 'norm', 'in_mask']), name='inputnode')
    outputnode = pe.Node(niu.IdentityInterface(
        fields=['out_surf']), name='outputnode')

    with open(pkgrf('regseg', 'data/%s.json' % model), 'rb' if PY2 else 'r') as sfh:
        labels = json.load(sfh)

    model_classes = list(labels.keys())
    exsurfs = extract_surface()
    exsurfs.get_node('inputnode').iterables = [
        ('name', model_classes),
        ('labels', [v for _, v in list(labels.items())]),
    ]

    wf = pe.Workflow(name=name)
    wf.connect([
        (inputnode, exsurfs,   [('aseg', 'inputnode.aseg'),
                                ('norm', 'inputnode.norm')]),
    ])

    if not gen_outer:
        wf.connect([
            (exsurfs,    outputnode, [('outputnode.out_surf', 'out_surf')]),
        ])
        return wf

    if gen_outer:
        m = pe.Node(niu.Merge(2), name='MergeSurfs')
        msk = extract_surface(name='MaskSurf')
        msk.inputs.inputnode.labels = [1]
        msk.inputs.inputnode.name = '%01d.outer' % (len(model_classes) - 1)

        wf.connect([
            (inputnode, msk, [('in_mask', 'inputnode.aseg'),
                              ('in_mask', 'inputnode.norm')]),
            (exsurfs,     m, [('outputnode.out_surf', 'in1')]),
            (msk,         m, [('outputnode.out_surf', 'in2')]),
            (m,  outputnode, [('out', 'out_surf')]),
        ])
    return wf


def _fillmask(in_file, in_filled=None):
    import nibabel as nb
    import numpy as np
    from nipype.interfaces.base import isdefined
    import os.path as op

    if in_filled is None or not isdefined(in_filled):
        return in_file

    nii = nb.load(in_file)
    data = nii.get_data()

    in_filled = np.atleast_1d(in_filled).tolist()
    for fname in in_filled:
        data = data + nb.load(fname).get_data()
    data[data > 1.0] = 1.0

    out_file = op.abspath('mask_filled.nii.gz')
    nb.Nifti1Image(data.astype(np.uint8), nii.get_affine(),
                   nii.get_header()).to_filename(out_file)
    return out_file
