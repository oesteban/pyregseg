#!/usr/bin/env python
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
Experiments on randomly generated phantoms
"""

from __future__ import print_function, division, absolute_import, unicode_literals
import os
import os.path as op


def get_parser():
    """ Command line interface for the phantom experiments """
    from argparse import ArgumentParser
    from argparse import RawTextHelpFormatter

    parser = ArgumentParser(description='Run evaluation workflow',
                            formatter_class=RawTextHelpFormatter)

    # Experimental Settings
    ################################
    g_input = parser.add_argument_group('Experimental Settings')
    g_input.add_argument(
        '-s', '--shape', action='store', default='gyrus', nargs='+',
        choices=['gyrus', 'ball', 'L', 'box'],
        help='selects phantom\'s shape model')
    g_input.add_argument(
        '-n', '--snr', action='store', nargs='+', type=int,
        help='generate signal with certain SNR')
    g_input.add_argument(
        '--no_cortex', action='store_false',
        help='do not generate cortex-like crust')
    g_input.add_argument(
        '--lo_matrix', action='store', default=51, type=int,
        help='low-resolution matrix size')
    g_input.add_argument(
        '--hi_matrix', action='store', default=101, type=int,
        help='hi-resolution matrix size')
    g_input.add_argument(
        '-g', '--grid_size', action='store', default=[4, 4, 4], nargs='+',
        type=int, help='number of control points')

    g_input.add_argument('-R', '--repetitions', action='store', default=1,
                         type=int, help='number of repetitions')

    # General Settings
    ################################
    g_settings = parser.add_argument_group('General settings')
    g_settings.add_argument(
        '-w', '--work_dir', action='store', default=os.getcwd(),
        help='directory where subjects are found')
    g_settings.add_argument(
        '-N', '--name', action='store', default='PhantomTests',
        help='default workflow name, it will create a new folder')
    g_settings.add_argument('--nthreads', action='store', default=0,
                            type=int, help='number of repetitions')
    g_settings.add_argument(
        '-D', '--data_dir', action='store',
        default=op.join(os.getenv('NEURO_DATA_HOME', os.getcwd()), 'phantoms'),
        help='directory where subjects are found')
    g_settings.add_argument('--debug', action='store_true', default=False,
                            help='switch debug mode ON')

    # Outputs
    ################################
    g_output = parser.add_argument_group('Outputs')
    g_output.add_argument(
        '-o', '--out_csv', action='store', default='phantoms_summary.csv',
        help='output summary csv file')
    return parser


def main():
    """Entry point"""
    from nipype import config, logging
    from regseg.workflows.phantoms import phantoms_wf

    options = get_parser().parse_args()

    # Setup multiprocessing
    nthreads = options.nthreads
    if nthreads == 0:
        from multiprocessing import cpu_count
        nthreads = cpu_count()

    cfg = {}
    cfg['plugin'] = 'Linear'
    if nthreads > 1:
        cfg['plugin'] = 'MultiProc'
        cfg['plugin_args'] = {'n_proc': nthreads}

    # Setup work_dir
    if not op.exists(options.work_dir):
        os.makedirs(options.work_dir)

    # Setup logging dir
    log_dir = op.abspath('logs')
    cfg['logging'] = {'log_directory': log_dir, 'log_to_file': True}
    if not op.exists(log_dir):
        os.makedirs(log_dir)

    config.update_config(cfg)
    logging.update_logging(config)

    wf = phantoms_wf(options, cfg)
    wf.base_dir = options.work_dir
    wf.write_graph(graph2use='hierarchical', format='pdf', simple_form=True)
    wf.run()


if __name__ == '__main__':
    main()
