from photutils.aperture import CircularAperture
from photutils.aperture import aperture_photometry
from photutils.aperture import CircularAnnulus
from matplotlib import pyplot as plt
import numpy as np
from astropy.stats import sigma_clipped_stats
import logging
_logger = logging.getLogger(__name__)

def redoAperturePhotometry (catalog, imagedata, aperture, annulus_inner, annulus_outer):
    """ Recalculate the FLUX column off a fits / BANZAI CAT extension based on operature photometry. """
    _logger.info ("redoing aperture photometry")
    positions = [ (catalog['x'][ii], catalog['y'][ii]) for ii in range (len(catalog['x'])) ]

    apertures = CircularAperture(positions, r=aperture)
    sky_apertures = CircularAnnulus(positions, r_in = annulus_inner, r_out = annulus_outer)
    sky_apertures_masks = sky_apertures.to_mask(method='center')
    bkg_median = []
    for mask in sky_apertures_masks:
        annulus_data = mask.multiply (imagedata)
        annulus_data_1d = annulus_data[mask.data>0]
        _, median_sigclip, _ = sigma_clipped_stats(annulus_data_1d)
        bkg_median.append (median_sigclip)
    bkg_median = np.array (bkg_median)

    phottable = aperture_photometry(imagedata, [apertures, sky_apertures])

    # plt.plot (phottable['aperture_sum_1'] / sky_apertures.area, phottable['aperture_sum_1'] / sky_apertures.area - bkg_median,'.')
    # plt.savefig ('sky.png')

    newflux = phottable['aperture_sum_0'] - bkg_median * apertures.area

    # oldmag = -2.5 * np.log10(catalog['FLUX'])
    # newmag = -2.5 * np.log10 (newflux)
    # _logger.info ( newmag - oldmag)
    # plt.plot (newmag, newmag - oldmag, '.')
    # plt.savefig("Comparison.png")

    catalog['FLUX'] = newflux
