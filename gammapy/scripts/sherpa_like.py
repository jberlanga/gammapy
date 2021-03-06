# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from ..utils.scripts import get_parser

__all__ = ['sherpa_image_like']


def main(args=None):
    parser = get_parser(sherpa_image_like)
    parser.add_argument('--counts', type=str, default='counts.fits',
                        help='Counts FITS file name')
    parser.add_argument('--exposure', type=str, default='exposure.fits',
                        help='Exposure FITS file name')
    parser.add_argument('--background', type=str, default='background.fits',
                        help='Background FITS file name')
    parser.add_argument('--psf', type=str, default='psf.json',
                        help='PSF JSON file name')
    parser.add_argument('--sources', type=str, default='sources.json',
                        help='Sources JSON file name (contains start '
                        'values for fit of Gaussians)')
    parser.add_argument('--roi', type=str, default='roi.reg',
                        help='Region of interest (ROI) file name (ds9 reg format)')
    parser.add_argument('outfile', type=str, default='fit_results.json',
                        help='Output JSON file with fit results')
    args = parser.parse_args(args)
    sherpa_image_like(**vars(args))


def sherpa_image_like(counts,
                      exposure,
                      background,
                      psf,
                      sources,
                      roi,
                      outfile):
    """Fit the morphology of a number of sources.

    Uses initial parameters from a JSON file (for now only Gaussians).
    """

    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
    import sherpa.astro.ui
    from ..morphology.utils import read_json, write_all
    from ..morphology.psf import Sherpa

    # ---------------------------------------------------------
    # Load images, PSF and sources
    # ---------------------------------------------------------
    logging.info('Clearing the sherpa session')
    sherpa.astro.ui.clean()

    logging.info('Reading counts: {0}'.format(counts))
    sherpa.astro.ui.load_data(counts)

    logging.info('Reading exposure: {0}'.format(exposure))
    sherpa.astro.ui.load_table_model('exposure', exposure)

    logging.info('Reading background: {0}'.format(background))
    sherpa.astro.ui.load_table_model('background', background)

    logging.info('Reading PSF: {0}'.format(psf))
    Sherpa(psf).set()

    if roi:
        logging.info('Reading ROI: {0}'.format(roi))
        sherpa.astro.ui.notice2d(roi)
    else:
        logging.info('No ROI selected.')

    logging.info('Reading sources: {0}'.format(sources))
    read_json(sources, sherpa.astro.ui.set_source)

    # ---------------------------------------------------------
    # Set up the full model and freeze PSF, exposure, background
    # ---------------------------------------------------------
    # Scale exposure by 1e-10 to get ampl or order unity and avoid some fitting problems
    name = sherpa.astro.ui.get_source().name
    full_model = 'background + 1e-10 * exposure * psf ({})'.format(name)
    sherpa.astro.ui.set_full_model(full_model)
    sherpa.astro.ui.freeze(background, exposure, psf)

    # ---------------------------------------------------------
    # Set up the fit
    # ---------------------------------------------------------
    sherpa.astro.ui.set_coord('physical')
    sherpa.astro.ui.set_stat('cash')
    sherpa.astro.ui.set_method('levmar')  # levmar, neldermead, moncar
    sherpa.astro.ui.set_method_opt('maxfev', int(1e3))
    sherpa.astro.ui.set_method_opt('verbose', 10)

    # ---------------------------------------------------------
    # Fit and save information we care about
    # ---------------------------------------------------------

    # show_all() # Prints info about data and model
    sherpa.astro.ui.fit()  # Does the fit
    sherpa.astro.ui.covar()  # Computes symmetric errors (fast)
    # conf() # Computes asymmetric errors (slow)
    # image_fit() # Shows data, model, residuals in ds9
    logging.info('Writing {}'.format(outfile))
    write_all(outfile)
