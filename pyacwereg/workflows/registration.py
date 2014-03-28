#!/usr/bin/env python
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#
# @Author: oesteban - code@oscaresteban.es
# @Date:   2014-03-28 20:38:30
# @Last Modified by:   oesteban
# @Last Modified time: 2014-03-28 20:48:15

import os
import os.path as op

import nipype.interfaces.io as nio              # Data i/o
import nipype.interfaces.utility as niu         # utility
import nipype.pipeline.engine as pe             # pipeline engine
import pyacwereg.nipype.interfaces as iface

def default_regseg( name='REGSEGDefault'):
    wf = pe.Workflow( name=name )

    inputnode = pe.Node(niu.IdentityInterface(fields=['in_orig', 'in_dist', 'in_tpms', 'in_surf' ]),
                                              name='outputnode' )

    outputnode = pe.Node(niu.IdentityInterface(fields=['out_corr', 'out_tpms', 'out_surf', 'out_field' ]),
                                               name='outputnode' )

    # Registration
    regseg = pe.Node( iface.ACWEReg(), name="ACWERegistration" )
    regseg.inputs.iterations = [ 10, 10 ]
    regseg.inputs.descript_update = [ 5, 15 ]
    regseg.inputs.step_size = [ 0.5, 1.0 ]
    regseg.inputs.alpha = [ 0.0, 0.001 ]
    regseg.inputs.beta = [ 0.0, 0.01 ]
    regseg.inputs.grid_size = [ 6, 10 ]
    regseg.inputs.convergence_energy = [ True, True ]
    regseg.inputs.convergence_window = [ 5, 5 ]

    # Apply tfm to tpms

    # Connect
    wf.connect([
         ( inputnode,   regseg, [ ('in_surfs','in_prior' ),
                                  ('in_dist','in_fixed' ) ])
        ,( regseg,  outputnode, [ ('out_warped','out_corr'),
                                  ('out_field','out_field'),
                                  ('out_surfs', 'out_surf')])
    ])