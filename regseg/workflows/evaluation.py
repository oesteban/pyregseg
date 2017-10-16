# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""Evaluating different SDC methods"""
from __future__ import print_function, division, absolute_import, unicode_literals
import os.path as op
import numpy as np

import nipype.pipeline.engine as pe             # pipeline engine
from nipype.interfaces import io as nio              # Data i/o
from nipype.interfaces import utility as niu         # utility
from nipype.algorithms import misc as namisc         # misc algorithms
from nipype.algorithms import mesh as namesh
from nipype.algorithms import metrics as namev

from ..interfaces.nilearn import Merge
from ..interfaces.warps import InverseField
from ..interfaces.utility import (HausdorffDistance,
                                  ComputeEnergy)


def registration_ev(name='EvaluateMapping'):
    """
    Workflow that provides different scores comparing two registration methods.
    It compares images similarity, displacement fields difference,
    mesh distances, and overlap indices.
    """

    def _stats(in_file):
        import numpy as np
        import nibabel as nb
        data = nb.load(in_file).get_data()
        if np.all(data < 1.0e-5):
            return [0.0] * 5
        data = np.ma.masked_equal(data, 0)
        result = np.array([data.mean(), data.std(), data.max(), data.min(),
                           np.ma.extras.median(data)])
        return result.tolist()

    def _get_id(inlist):
        return range(len(inlist))

    input_ref = pe.Node(niu.IdentityInterface(
        fields=['in_imag', 'in_tpms', 'in_surf', 'in_field', 'in_mask']),
        name='refnode')
    input_tst = pe.Node(niu.IdentityInterface(
        fields=['in_imag', 'in_tpms', 'in_surf', 'in_field']),
        name='tstnode')
    inputnode = pe.Node(niu.IdentityInterface(
        fields=['snr', 'shape', 'method', 'repetition',
                'resolution', 'out_csv']),
        name='infonode')
    outputnode = pe.Node(niu.IdentityInterface(
        fields=['out_file', 'out_tpm_diff', 'out_field_err']),
        name='outputnode')
    merge_ref = pe.Node(Merge(), name='ConcatRefInputs')
    merge_tst = pe.Node(Merge(), name='ConcatTestInputs')
    overlap = pe.Node(namev.FuzzyOverlap(weighting='volume'), name='Overlap')
    diff_im = pe.Node(namev.Similarity(metric='cc'), name='ContrastDiff')
    inv_fld = pe.Node(InverseField(), name='InvertField')
    diff_fld = pe.Node(namev.ErrorMap(), name='FieldDiff')
    mesh = pe.MapNode(HausdorffDistance(cells_mode=True),
                      iterfield=['surface1', 'surface2'],
                      name='SurfDistance')
    csv = pe.MapNode(namisc.AddCSVRow(infields=['surf_id', 'surfdist_avg']),
                     name="AddRow", iterfield=['surf_id', 'surfdist_avg'])
    wf = pe.Workflow(name=name)
    wf.connect([
        (inputnode,        csv, [('shape', 'model_type'),
                                 ('snr', 'snr'),
                                 ('method', 'method'),
                                 ('resolution', 'resolution'),
                                 ('repetition', 'repetition'),
                                 ('out_csv', 'in_file')]),
        # (input_ref,  merge_ref, [('in_imag', 'in_files')]),
        # (input_tst,  merge_tst, [('in_imag', 'in_files')]),
        # (input_ref,    overlap, [('in_tpms', 'in_ref')]),
        # (input_tst,    overlap, [('in_tpms', 'in_tst')]),
        # (input_ref,    diff_im, [('in_mask', 'mask1'),
        #                          ('in_mask', 'mask2')]),
        # (merge_ref,    diff_im, [('merged_file', 'volume1')]),
        # (merge_tst,    diff_im, [('merged_file', 'volume2')]),
        # (input_ref,    inv_fld, [('in_field', 'in_field')]),
        # (input_ref,   diff_fld, [('in_mask', 'mask')]),
        # (inv_fld,     diff_fld, [('out_field', 'in_ref')]),
        # (input_tst,   diff_fld, [('in_field', 'in_tst')]),
        # (overlap,          csv, [('jaccard', 'fji_avg'),
        #                          ('class_fji', 'fji_tpm'),
        #                          ('dice', 'fdi_avg'),
        #                          ('class_fdi', 'fdi_tpm')]),
        # (diff_im,          csv, [('similarity', 'cc_image')]),
        # (diff_fld,         csv, [(('out_map', _stats), 'fmap_error')]),
        # (csv,       outputnode, [('csv_file', 'out_file')]),
        # (overlap,   outputnode, [('diff_file', 'out_tpm_diff')]),
        # (diff_fld,  outputnode, [('out_map', 'out_field_err')]),
        (input_ref,       mesh, [('in_surf', 'surface1')]),
        (input_tst,       mesh, [('in_surf', 'surface2')]),
        (mesh,             csv, [('avg_hd', 'surfdist_avg'),
                                 (('avg_hd', _get_id), 'surf_id')])
        # (mesh,             csv, [('max_hd', 'surfdist_hausdorff'),
        #                          ('avg_hd', 'surfdist_avg'),
        #                          ('std_hd', 'surfdist_std'),
        #                          ('stats_hd', 'surfdist_stats')])
    ])
    return wf


def map_energy(name='EnergyMapping', out_csv='energiesmapping.csv'):

    out_csv = op.abspath(out_csv)
    inputnode = pe.Node(niu.IdentityInterface(
        fields=['reference', 'surfaces0', 'surfaces1', 'in_mask',
                'subject_id']), name='inputnode')
    outputnode = pe.Node(niu.IdentityInterface(
        fields=['desc_zero', 'out_diff']), name='outputnode')

    ref_e = pe.Node(ComputeEnergy(), name='ComputeZeroEnergy')
    diff = pe.MapNode(namesh.ComputeMeshWarp(), name='ComputeError',
                      iterfield=['surface1', 'surface2'])

    getval = pe.Node(nio.JSONFileGrabber(), name='GetZeroEnergy')
    csv = pe.Node(namisc.AddCSVRow(in_file=out_csv),
                  name="AddReferenceRow")
    csv.inputs.error = 0.0

    mapper = warp_n_map(out_csv=out_csv)
    wf = pe.Workflow(name=name)
    wf.connect([
        (inputnode,     ref_e,  [('reference', 'reference'),
                                 ('surfaces0', 'surfaces'),
                                 ('in_mask', 'in_mask')]),
        (ref_e,     outputnode, [('out_file', 'desc_zero')]),
        (ref_e,         getval, [('out_file', 'in_file')]),
        (inputnode,        csv, [('subject_id', 'subject_id')]),
        (getval,           csv, [('total', 'total')]),
        (inputnode,       diff, [('surfaces0', 'surface1'),
                                 ('surfaces1', 'surface2')]),

        (diff,      outputnode, [('out_warp', 'out_diff')]),

        (inputnode,     mapper, [('subject_id', 'inputnode.subject_id'),
                                 ('reference', 'inputnode.reference'),
                                 ('in_mask', 'inputnode.in_mask')]),
        (diff,          mapper, [('out_warp', 'inputnode.surf_warp')]),
        (ref_e,         mapper, [('out_desc', 'inputnode.descriptors')])
    ])
    return wf


def warp_n_map(name='EnergyWarpAndMap', out_csv='energies.csv'):
    inputnode = pe.Node(niu.IdentityInterface(
        fields=['reference', 'surf_warp', 'in_mask', 'errfactor',
                'descriptors', 'subject_id']), name='inputnode')
    inputnode.iterables = ('errfactor', np.linspace(-1.2, 1.2, num=100,
                                                    endpoint=True).tolist())

    outputnode = pe.Node(niu.IdentityInterface(
        fields=['out_energy']), name='outputnode')

    applyef = pe.MapNode(
        namesh.MeshWarpMaths(operation='mul'), name='MeshMaths',
        iterfield=['in_surf'])
    mapeneg = pe.Node(ComputeEnergy(), name='ComputeEnergy')
    getval = pe.Node(nio.JSONFileGrabber(), name='GetEnergy')

    wf = pe.Workflow(name=name)
    wf.connect([
        (inputnode,    applyef, [('surf_warp', 'in_surf'),
                                 ('errfactor', 'operator')]),
        (applyef,      mapeneg, [('out_file', 'surfaces')]),
        (inputnode,    mapeneg, [('reference', 'reference'),
                                 ('in_mask', 'in_mask'),
                                 ('descriptors', 'descriptors')]),
        (mapeneg,       getval, [('out_file', 'in_file')]),
        (mapeneg,   outputnode, [('out_file', 'out_energy')])
    ])

    csv = pe.Node(namisc.AddCSVRow(in_file=out_csv),
                  name="AddRow")

    wf.connect([
        (getval,           csv, [('total', 'total')]),
        (inputnode,        csv, [('errfactor', 'error'),
                                 ('subject_id', 'subject_id')])
    ])

    return wf
