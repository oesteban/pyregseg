#!/usr/bin/env python
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
Image tools interfaces
~~~~~~~~~~~~~~~~~~~~~~


"""
from __future__ import absolute_import, unicode_literals, division, print_function
import nibabel as nb
import numpy as np
from nilearn.image import concat_imgs, iter_img

from nipype import logging
from nipype.utils.filemanip import fname_presuffix
from nipype.interfaces.base import (
    traits, isdefined, TraitedSpec, BaseInterfaceInputSpec,
    File, InputMultiPath, OutputMultiPath, SimpleInterface
)

LOGGER = logging.getLogger('interface')


class MergeInputSpec(BaseInterfaceInputSpec):
    in_files = InputMultiPath(File(exists=True), mandatory=True,
                              desc='input list of files to merge')
    dtype = traits.Enum('f4', 'f8', 'u1', 'u2', 'u4', 'i2', 'i4',
                        usedefault=True, desc='numpy dtype of output image')
    header_source = File(exists=True, desc='a Nifti file from which the header should be copied')
    compress = traits.Bool(True, usedefault=True, desc='Use gzip compression on .nii output')


class MergeOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='output merged file')


class Merge(SimpleInterface):
    input_spec = MergeInputSpec
    output_spec = MergeOutputSpec

    def _run_interface(self, runtime):
        ext = '.nii.gz' if self.inputs.compress else '.nii'
        self._results['out_file'] = fname_presuffix(
            self.inputs.in_files[0], suffix='_merged' + ext, newpath=runtime.cwd, use_ext=False)
        new_nii = concat_imgs(self.inputs.in_files, dtype=self.inputs.dtype)

        if isdefined(self.inputs.header_source):
            src_hdr = nb.load(self.inputs.header_source).header
            new_nii.header.set_xyzt_units(t=src_hdr.get_xyzt_units()[-1])
            new_nii.header.set_zooms(list(new_nii.header.get_zooms()[:3]) +
                                     [src_hdr.get_zooms()[3]])

        new_nii.to_filename(self._results['out_file'])

        return runtime


class SplitInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True,
                   desc='input 4D file of files to be split')
    compress = traits.Bool(True, usedefault=True, desc='Use gzip compression on .nii output')


class SplitOutputSpec(TraitedSpec):
    out_files= OutputMultiPath(File(exists=True), desc='output merged file')


class Split(SimpleInterface):
    input_spec = SplitInputSpec
    output_spec = SplitOutputSpec

    def _run_interface(self, runtime):
        ext = '.nii.gz' if self.inputs.compress else '.nii'
        self._results['out_files'] = []
        out_pattern = fname_presuffix(self.inputs.in_file, suffix='_%05d' + ext,
                                      newpath=runtime.cwd, use_ext=False)

        for i, im in enumerate(iter_img(nb.load(self.inputs.in_file))):
            out_file = out_pattern % i
            im.to_filename(out_file)
            self._results['out_files'].append(out_file)
        return runtime


class BinarizeInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True,
                   desc='input file')
    threshold = traits.Float(0.0, usedefault=True,
                             desc='threshold')
    match = traits.List(traits.Int,
                        desc='match instead of threshold')


class BinarizeOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='output binary mask')


class Binarize(SimpleInterface):
    input_spec = BinarizeInputSpec
    output_spec = BinarizeOutputSpec

    def _run_interface(self, runtime):
        self._results['out_file'] = fname_presuffix(
            self.inputs.in_file, suffix='_mask', newpath=runtime.cwd)

        nii = nb.load(self.inputs.in_file)
        data = nii.get_data()
        mask = np.zeros_like(data, dtype=np.uint8)
        hdr = nii.header.copy()
        hdr.set_data_dtype(np.uint8)

        if isdefined(self.inputs.match) and self.inputs.match:
            for label in self.inputs.match:
                mask[data == label] = 1
        else:
            mask[data >= self.inputs.threshold] = 1

        new = nii.__class__(mask, nii.affine, hdr)
        new.to_filename(self._results['out_file'])
        return runtime

