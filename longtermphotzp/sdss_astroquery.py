import logging

import numpy as np
from astropy import coordinates as coords
from astropy import units as u
from astropy.table import Table
from astroquery.sdss import SDSS

from longtermphotzp.atlasrefcat2 import atlas_refcat2

_logger = logging.getLogger(__name__)

# Maps SDSS photoobj field names to the column names used by the atlas_refcat2 photometric table.
SDSS_TO_REFCAT2_COLUMNS = {
    'u': 'umag', 'err_u': 'umagerr',
    'g': 'gmag', 'err_g': 'gmagerr',
    'r': 'rmag', 'err_r': 'rmagerr',
    'i': 'imag', 'err_i': 'imagerr',
    'z': 'zmag', 'err_z': 'zmagerr',
}


def get_reference_catalog(ra, dec, width=30):
    """
    Query the SDSS photometric catalog for a rectangular region centered on (ra, dec).

    :param ra: Right ascension of the field center, in degrees.
    :param dec: Declination of the field center, in degrees.
    :param width: Width (and height) of the rectangular search box, in arcminutes. Defaults to 30.
    :return: astropy.table.Table with columns ra, dec, umag, umagerr, gmag, gmagerr, rmag, rmagerr,
             imag, imagerr, zmag, zmagerr, compatible with the table returned by
             atlasrefcat2.atlas_refcat2.get_reference_catalog. Returns None on failure or no matches.
    """
    try:
        position = coords.SkyCoord(ra=ra * u.degree, dec=dec * u.degree, frame='icrs')
        boxsize = width * u.arcmin

        photoobj_fields = ['ra', 'dec'] + list(SDSS_TO_REFCAT2_COLUMNS.keys())
        result = SDSS.query_region(position, width=boxsize, height=boxsize,
                                    photoobj_fields=photoobj_fields)
    except Exception as e:
        _logger.exception(f"While querying SDSS photometric catalog: {e}")
        return None

    if result is None or len(result) == 0:
        _logger.warning(f"SDSS query returned no sources for ra={ra}, dec={dec}, width={width} arcmin")
        return None

    table = Table()
    table['ra'] = np.array(result['ra'], dtype=np.float32)
    table['dec'] = np.array(result['dec'], dtype=np.float32)
    for sdss_name, refcat2_name in SDSS_TO_REFCAT2_COLUMNS.items():
        table[refcat2_name] = np.array(result[sdss_name], dtype=np.float32)

    table = table[(table['rmagerr']<0.025) & (table['gmagerr']<0.025) & (table['imagerr']<0.025) & (table['zmagerr']<0.025)]
    return table


class sdss_refcat2(atlas_refcat2):
    """ Drop-in replacement for atlas_refcat2 that sources its photometry from SDSS instead of refcat2. """

    def __init__(self):
        pass  # no catalog service URL needed, queries go straight to astroquery.sdss.SDSS

    def get_reference_catalog(self, ra, dec, radius, generateJohnson=False):
        # radius is a circular search radius in degrees, matching atlas_refcat2's convention.
        width = 2 * radius * 60
        table = get_reference_catalog(ra, dec, width=width)
        if table is None:
            return None

        if generateJohnson:
            table = self.SDSS2Johnson(table)

        return table

