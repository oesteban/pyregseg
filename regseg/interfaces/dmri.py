#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: oesteban
# @Date:   2015-03-10 16:15:07
# @Last Modified by:   oesteban
# @Last Modified time: 2015-04-13 11:49:09

import os
import os.path as op
import nibabel as nb
import numpy as np

from nipype.interfaces.base import (BaseInterface, traits, TraitedSpec, File,
                                    InputMultiPath, OutputMultiPath,
                                    BaseInterfaceInputSpec, isdefined,
                                    DynamicTraitedSpec, Directory,
                                    CommandLine, CommandLineInputSpec)

from nipype import logging
iflogger = logging.getLogger('interface')


class PhaseUnwrapInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True,
                   desc='phase file to be unwrapped')
    in_mask = File(exists=True, desc='mask file')
    rescale = traits.Bool(True, usedefault=True,
                          desc='rescale range to 2*pi')
    denoise = traits.Bool(True, usedefault=True,
                          desc='fit into original data')
    fitting = traits.Bool(False, usedefault=True,
                          desc='fit into original data')
    out_file = File('unwrapped.nii.gz', usedefault=True,
                    desc='output file name')


class PhaseUnwrapOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='output file name')
    te_diff = traits.Float(desc=('echo-time difference in mapping'
                                 ' sequence'))


class PhaseUnwrap(BaseInterface):

    """
    Unwraps a phase file
    """
    input_spec = PhaseUnwrapInputSpec
    output_spec = PhaseUnwrapOutputSpec

    def _run_interface(self, runtime):
        from skimage.restoration import unwrap_phase as unwrap
        from scipy.ndimage import median_filter as denoise
        from math import pi

        im = nb.load(self.inputs.in_file)
        refdata = im.get_data()
        refdata -= np.median(refdata)
        wrapped = refdata

        msk = np.ones_like(wrapped)
        if isdefined(self.inputs.in_mask):
            msk = nb.load(self.inputs.in_mask).get_data()
            msk[msk > 0.0] = 1.0
            msk[msk < 1.0] = 0.0

        if self.inputs.rescale:
            te_diff1 = pi / wrapped.max()
            te_diff2 = abs(pi / wrapped.min())
            te_diff = 0.5 * (te_diff1 + te_diff2)

            refdata[refdata > 0] *= te_diff1
            refdata[refdata < 0] *= te_diff2
            wrapped = refdata * 2.75
            wrapped[wrapped >= (pi - 1.0e-5)] -= 2.0 * pi
            wrapped[wrapped < -pi] += 2.0 * pi
            self._te_diff = te_diff

        nb.Nifti1Image(wrapped, im.get_affine(),
                       im.get_header()).to_filename('wrapped.nii.gz')
        nb.Nifti1Image(refdata, im.get_affine(),
                       im.get_header()).to_filename('refdata.nii.gz')

        smoothed = unwrap(wrapped, wrap_around=True).astype(np.float32)

        nb.Nifti1Image(smoothed, im.get_affine(),
                       im.get_header()).to_filename('unwrapped0.nii.gz')

        if self.inputs.denoise:
            unw = smoothed.copy()
            smoothed = denoise(np.ma.array(smoothed, mask=1 - msk),
                               4).astype(np.float32)
            smoothed -= np.median(smoothed)
            nb.Nifti1Image(smoothed, im.get_affine(),
                           im.get_header()).to_filename('denoised.nii.gz')

        if self.inputs.fitting:
            fitmsk = msk.copy()
            maxv = np.percentile(smoothed[msk > 0], 85)
            minv = np.percentile(smoothed[msk > 0], 15)
            fitmsk[smoothed > maxv] = 0
            fitmsk[smoothed < minv] = 0
            fitmsk[smoothed == 0.0] = 0
            # pha_err = unw - wrapped
            # fitmsk[pha_err < 0] = 0
            # fitmsk[pha_err > 0] = 0

            nb.Nifti1Image(fitmsk, im.get_affine(),
                           im.get_header()).to_filename('msk.nii.gz')
            x = refdata[fitmsk > 0].reshape(-1)
            y = smoothed[fitmsk > 0].reshape(-1)
            m = np.abs(x).sum() / np.abs(y).sum()
            smoothed *= m

        if isdefined(self.inputs.in_mask):
            smoothed *= msk

        hdr = im.get_header().copy()
        hdr.set_data_dtype(np.float32)
        nb.Nifti1Image(smoothed.astype(np.float32), im.get_affine(),
                       hdr).to_filename(op.abspath(self.inputs.out_file))
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_file'] = op.abspath(self.inputs.out_file)

        try:
            outputs['te_diff'] = self._te_diff
        except AttributeError:
            pass

        return outputs
