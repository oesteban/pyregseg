#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: oesteban
# @Date:   2014-11-19 09:46:07
# @Last Modified by:   oesteban
# @Last Modified time: 2015-03-03 15:19:23
import os
import os.path as op
from glob import glob
import nibabel as nb
import numpy as np

from nipype.interfaces.base import (BaseInterface, traits, TraitedSpec, File,
                                    InputMultiPath, OutputMultiPath,
                                    BaseInterfaceInputSpec, isdefined,
                                    DynamicTraitedSpec, Directory,
                                    CommandLine, CommandLineInputSpec)

from nipype import logging
iflogger = logging.getLogger('interface')


class ExportSlicesInputSpec(CommandLineInputSpec):
    reference = File(exists=True, argstr='-i %s', mandatory=True,
                     desc=('reference image to show in background'))
    surfaces0 = InputMultiPath(
        File(exists=True), argstr='-S %s',
        desc=('vtk contours that will be overlaid on reference'))
    surfaces1 = InputMultiPath(
        File(exists=True), argstr='-R %s',
        desc=('vtk contours that will be overlaid on reference'))
    surfaces3 = InputMultiPath(
        File(exists=True), argstr='-O %s',
        desc=('vtk contours that will be overlaid on reference'))

    num_slices = traits.Int(14, argstr='-n %d', desc='total num. of slices')
    axis = traits.Enum(2, 0, 1, argstr='-a %d', usedefault=True,
                       desc='axis to cut through')
    all_axis = traits.Bool(argstr='-A', desc='slice through all axes')


class ExportSlicesOutputSpec(TraitedSpec):
    out_files = OutputMultiPath(File(exists=True), desc='output files')


class ExportSlices(CommandLine):

    """
    Export slices produces visualization through the selected axis
    of the input image and contours
    """
    input_spec = ExportSlicesInputSpec
    output_spec = ExportSlicesOutputSpec
    _cmd = 'xvfb-run -a -s "-screen 0 640x480x24" slice_contours'
    _redirect_x = False

    def _list_outputs(self):
        from glob import glob
        outputs = self.output_spec().get()
        out_path = os.getcwd()
        out_pattern = op.join(out_path, '*.png')
        outputs['out_files'] = sorted(glob(out_pattern))
        return outputs


class SlicesGridplotInputSpec(BaseInterfaceInputSpec):
    slices = File(exists=True, mandatory=True, desc='input slices list')
    view = traits.Enum('axial', 'coronal', 'sagittal', 'all', usedefault=True,
                       desc='view plane to export')
    out_file = File('slices_gridplot.pdf',
                    usedefault=True, desc='output report')


class SlicesGridplotOutputSpec(BaseInterfaceInputSpec):
    out_file = File(desc='output report')


class SlicesGridplot(BaseInterface):
    input_spec = SlicesGridplotInputSpec
    output_spec = SlicesGridplotOutputSpec

    def _run_interface(self, runtime):
        from pyacwereg import viz

        view = [self.inputs.view]
        if self.inputs.view == 'all':
            view = ['axial', 'coronal', 'sagittal']

        viz.slices_gridplot(self.inputs.slices, view=view,
                            out_file=op.abspath(self.inputs.out_file))
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = op.abspath(self.inputs.out_file)
        return outputsOutputSpec


class Surf2VolInputSpec(CommandLineInputSpec):
    reference = File(exists=True, argstr='-R %s', mandatory=True,
                     desc=('reference image grid'))
    surfaces = InputMultiPath(
        File(exists=True), argstr='-S %s', mandatory=True,
        desc=('vtk contours that will be mapped to volume'))
    out_prefix = traits.Str('surf2vol', argstr='-o %s', usedefault=True,
                            desc='output files prefix')


class Surf2VolOutputSpec(TraitedSpec):
    out_tpm = OutputMultiPath(File(exists=True),
                              desc='output tissue probability maps')
    out_seg = File(exists=True, desc='output segmentation')


class Surf2Vol(CommandLine):

    """
    Converts surface contours defining regions in space to volumes
    """
    input_spec = Surf2VolInputSpec
    output_spec = Surf2VolOutputSpec
    _cmd = 'binarize_surfaces'

    def _list_outputs(self):
        outputs = self.output_spec().get()
        out_path = op.abspath(self.inputs.out_prefix)
        outputs['out_tpm'] = [op.abspath(f) for f in sorted(glob(
            op.basename(out_path + '_tpm_cmp*.nii.gz')))]
        outputs['out_seg'] = out_path + '_seg.nii.gz'
        return outputs


class HausdorffDistanceInputSpec(CommandLineInputSpec):
    surface1 = File(exists=True, argstr='-r %s', mandatory=True,
                    desc=('reference surface'))
    surface2 = File(exists=True, argstr='-t %s', mandatory=True,
                    desc=('reference surface'))
    cells_mode = traits.Bool(False, argstr='-C',
                             desc='Use point-to-cells mode')
    out_ref = File('hdist_ref.vtk', usedefault=True,
                   desc='Output reference file name')
    out_tst = File('hdist_ref.vtk', usedefault=True,
                   desc='Output reference file name')


class HausdorffDistanceOutputSpec(TraitedSpec):
    out_ref = File(exists=True,
                   desc='Output reference file name')
    out_tst = File(exists=True,
                   desc='Output test file name')
    max_hd = traits.Float(desc='maximum of distances (Hausdorff distance)')
    avg_hd = traits.Float(desc='average distance')
    std_hd = traits.Float(desc='standard deviation of distance')
    stats_hd = traits.List(traits.Float(), desc='distance statistics')


class HausdorffDistance(CommandLine):

    """
    Converts surface contours defining regions in space to volumes
    """
    input_spec = HausdorffDistanceInputSpec
    output_spec = HausdorffDistanceOutputSpec
    _cmd = 'hdistance'

    def _list_outputs(self):
        outputs = self.output_spec().get()

        outputs['out_ref'] = op.abspath(self.inputs.out_ref)
        outputs['out_tst'] = op.abspath(self.inputs.out_tst)
        outputs['max_hd'] = 0.0
        outputs['avg_hd'] = 0.0
        outputs['std_hd'] = 0.0
        outputs['stats_hd'] = [0.0] * 7

        try:
            from tvtk.api import tvtk
        except ImportError:
            raise ImportError('Interface HausdorffDistance requires tvtk')

        try:
            from enthought.etsconfig.api import ETSConfig
            ETSConfig.toolkit = 'null'
        except ImportError:
            iflogger.warn(('ETS toolkit could not be imported'))
            pass

        try:
            r = tvtk.PolyDataReader(file_name=op.abspath(self.inputs.out_ref))
            v = r.output
            r.update()
            points = np.array(v.point_data.get_array('Distance'))
            outputs['max_hd'] = points.max()
            outputs['avg_hd'] = points.mean()
            outputs['std_hd'] = points.std()
            outputs['stats_hd'] = [points.min(),
                                   np.percentile(points, 5.0),
                                   np.percentile(points, 25.0),
                                   np.median(points),
                                   np.percentile(points, 75.0),
                                   np.percentile(points, 95.0),
                                   points.max()]
        except:
            iflogger.warn('Hausdorff distance could not be computed')
            pass

        return outputs


class ComputeEnergyInputSpec(CommandLineInputSpec):
    reference = InputMultiPath(
        File(exists=True), argstr='-R %s', mandatory=True,
        desc=('reference image grid'))
    surfaces = InputMultiPath(
        File(exists=True), argstr='-S %s', mandatory=True,
        desc=('vtk contours that will be mapped to volume'))

    in_mask = File(exists=True, argstr='-M %s', desc='mask file')
    descriptors = File(
        exists=True, argstr='-D %s', desc='descriptors JSON file')

    out_file = File('energies.json', argstr='-o %s', usedefault=True,
                    mandatory=True, desc='output file name')


class ComputeEnergyOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='output file name')
    out_desc = File(desc='output descriptors')


class ComputeEnergy(CommandLine):

    """
    Compute energy of reference image given a set of contours.
    """
    input_spec = ComputeEnergyInputSpec
    output_spec = ComputeEnergyOutputSpec
    _cmd = 'regseg_energytest'

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = op.abspath(self.inputs.out_file)

        if not isdefined(self.inputs.descriptors):
            outputs['out_desc'] = op.abspath('descriptors.json')
        return outputs


class SigmoidFilterInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True,
                   desc='input image')
    in_mask = File(exists=True, desc='binary mask')
    max_out = traits.Float(2000.0, mandatory=True, usedefault=True,
                           desc='fit maximum value of output')
    upper_perc = traits.Float(92.0, mandatory=True, usedefault=True,
                              desc='upper percentile for computations')
    lower_perc = traits.Float(2.0, mandatory=True, usedefault=True,
                              desc='lower percentile for computations')
    out_file = File('enhanced.nii.gz', usedefault=True, desc='enhanced image')


class SigmoidFilterOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='enhanced image')


class SigmoidFilter(BaseInterface):

    """
    An enhancement filter for MI-based registrations


    Example
    -------
    >>> from pyacwereg.interfaces.utility import SigmoidFilter
    >>> enh = SigmoidFilter()
    >>> enh.inputs.in_file = 'T2.nii.gz'
    >>> result = enh.run() # doctest: +SKIP

    """
    input_spec = SigmoidFilterInputSpec
    output_spec = SigmoidFilterOutputSpec

    def _run_interface(self, runtime):
        from pyacwereg.filters import sigmoid_filter

        im = nb.load(self.inputs.in_file)
        msk = None

        if isdefined(self.inputs.in_mask):
            msk = nb.load(self.inputs.in_mask).get_data()

        lower = self.inputs.lower_perc
        upper = self.inputs.upper_perc
        maxout = self.inputs.max_out

        enhanced = sigmoid_filter(im.get_data(), msk,
                                  a=lower, b=upper, maxout=maxout)

        nb.Nifti1Image(enhanced, im.get_affine(), im.get_header()).to_filename(
            op.abspath(self.inputs.out_file))

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_file'] = op.abspath(self.inputs.out_file)
        return outputs
