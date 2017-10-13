#!/usr/bin/env python
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
A wrapper for RegSeg to provide a more usable interface

"""
from __future__ import absolute_import, division, print_function, unicode_literals


def get_parser():
    """Build parser object"""
    from argparse import ArgumentParser
    from argparse import RawTextHelpFormatter

    parser = ArgumentParser(description='A wrapper for RegSeg',
                            formatter_class=RawTextHelpFormatter)

    g_surfaces = parser.add_mutually_exclusive_group(required=True)
    g_surfaces.add_argument('-S', '--moving-surfaces', nargs='+', action='store',
                            help='input surfaces in VTK format, nested from interior to exterior')
    g_surfaces.add_argument('-P', '--parc-file', action='store',
                            help='input parcellation file in NifTI format')

    g_target = parser.add_mutually_exclusive_group(required=True)
    g_target.add_argument('--dwi', action='store',
                          help='preprocessed DWI: fits a DTI model (from MRTrix) and uses '
                               'the FA and MD maps as volumetric target')
    g_target.add_argument('--bold', action='store',
                          help='preprocessed BOLD: calculates the non-steady states of the input '
                               'time-series and calculates the average to be used as target')
    g_target.add_argument('--fixed-volume', nargs='+', action='store',
                          help='list of target maps to be used as target features in fixed space')
    return parser


def main():
    """Entry point"""
    from nipype.pipeline import engine as pe
    from nipype.interfaces import utility as niu

    from ..workflows.registration import regseg_wf
    opts = get_parser().parse_args()

    wf = pe.Workflow(name='RegSegWrapper')
    regseg = regseg_wf(usemask=True)

    if opts.moving_surfaces is not None:
        surfnode = pe.Node(niu.IdentityInterface(fields=['in_surf']), name='surfinput')
        surfnode.inputs.in_surf = opts.moving_surfaces
        wf.connect(surfnode, 'in_surf', regseg, 'in_surf')

    if opts.fixed_volume is not None:
        fixednode = pe.Node(niu.IdentityInterface(fields=['in_fixed']), name='volumeinput')
        fixednode.inputs.inputnode.in_fixed = opts.fixed_volume
        wf.connect(fixednode, 'in_fixed', regseg, 'in_fixed')

    if opts.dwi is not None:
        from ..workflows.dti import mrtrix_dti

        mdti = pe.Node(niu.Merge(2), name='MergeDTI')
        dti_wf = mrtrix_dti('FitDTI')
        dti_wf.inputs.inputnode.in_dwi = opts.dwi
        # dti_wf.inputs.inputnode.in_mask = opts.mask
        # dti_wf.inputs.inputnode.in_bvec = opts.mask
        # dti_wf.inputs.inputnode.in_bval = opts.mask

        wf.connect([
            (dti_wf, mdti, [('outputnode.fa', 'in1'),
                            ('outputnode.md', 'in2')]),
            (mdti, regseg, [('out', 'inputnode.in_fixed')]),
        ])

    if opts.parc_file is not None:
        from ..workflows.surfaces import all_surfaces

        surf_wf = all_surfaces()
        surf_wf.inputs.inputnode.aseg = opts.parc_file
        # surf_wf.inputs.inputnode.norm = opts.norm
        # surf_wf.inputs.inputnode.in_mask = opts.mask
        wf.connect([
            (surf_wf, regseg, [('outputnode.out_surf', 'inputnode.in_surf')]),
        ])

    wf.run()


if __name__ == '__main__':
    main()
