# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
Handling surfaces

"""
from __future__ import absolute_import, unicode_literals, division, print_function
import subprocess as sp

import nibabel as nb
import numpy as np

from nipype import logging
from nipype.utils.filemanip import fname_presuffix
from nipype.interfaces.base import (
    traits, isdefined, TraitedSpec, BaseInterfaceInputSpec,
    File, InputMultiPath, OutputMultiPath, SimpleInterface
)


class FixVTKInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True,
                   desc='the input VTK file')
    in_ref = File(exists=True, mandatory=True,
                  desc='the reference nifti file')


class FixVTKOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='fixed VTK file')


class FixVTK(SimpleInterface):
    """
    Transforms a vtk file from Freesurfer's *tkRAS* coordinates
    to a target image in *scannerRAS* coordinates.
    """
    input_spec = FixVTKInputSpec
    output_spec = FixVTKOutputSpec

    def _run_interface(self, runtime):
        out_file = fname_presuffix(self.inputs.in_file, suffix='_fixed',
                                   newpath=runtime.cwd)

        self._results['out_file'] = _fixvtk(
            self.inputs.in_file, self.inputs.in_ref, out_file)
        return runtime

def _fixvtk(in_file, in_ref, out_file):
    ref = nb.load(in_ref)
    cmd_info = "mri_info %s  --tkr2scanner" % in_ref
    proc = sp.Popen(cmd_info, stdout=sp.PIPE, shell=True)
    data = bytearray(proc.stdout.read())
    if 'niiRead'.encode() in data:
        _, data = data.split('\n', 1)

    mstring = np.fromstring(data.decode("utf-8"), sep='\n')
    matrix = np.reshape(mstring, (4, -1))

    with open(in_file, 'r') as f:
        with open(out_file, 'w+') as w:
            npoints = 0
            pointid = -5

            for i, l in enumerate(f):
                if i == 4:
                    s = l.split()
                    npoints = int(s[1])
                    fmt = np.dtype(s[2])
                elif i > 4 and pointid < npoints:
                    vert = [float(x) for x in l.split()]
                    vert.append(1.0)
                    newvert = np.dot(matrix, vert)
                    l = '%.9f  %.9f  %.9f\n' % tuple(newvert[0:3])

                w.write(l)
                pointid = pointid + 1

    return out_file
