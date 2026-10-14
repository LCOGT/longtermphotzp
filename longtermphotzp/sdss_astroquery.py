import logging
import math

import numpy as np
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

# Photometric quality cut, same as applied to the atlas refcat2 catalog.
MAX_MAGERR = 0.025


class SkyServerRefusedError(Exception):
    """ SkyServer answered with an HTML error page instead of a result table, typically when throttling a client. """


def _build_query(ra, dec, width):
    """
    Build a SkyServer SQL query for primary stars with good griz photometry in a box centered on (ra, dec).

    Querying PhotoObj (primary detections only) with type = 6 (stars) and pushing the error cut into the query
    reduces the result ~5x compared to astroquery's query_region, which pulls every detection from PhotoObjAll.
    """
    halfwidth = width / 60. / 2.
    decmin = max(dec - halfwidth, -90.)
    decmax = min(dec + halfwidth, 90.)
    # widen the RA range with declination so the box covers the same sky area.
    cosdec = math.cos(math.radians(min(abs(dec) + halfwidth, 90.)))
    rahalfwidth = halfwidth / cosdec if cosdec > 1e-6 else 180.

    if rahalfwidth >= 180.:
        racondition = '1 = 1'
    else:
        ramin = (ra - rahalfwidth) % 360.
        ramax = (ra + rahalfwidth) % 360.
        if ramin <= ramax:
            racondition = f'p.ra BETWEEN {ramin:.6f} AND {ramax:.6f}'
        else:
            # box straddles RA = 0
            racondition = f'(p.ra >= {ramin:.6f} OR p.ra <= {ramax:.6f})'

    # err > 0 also rejects SDSS's -9999 placeholders for missing measurements.
    errcondition = ' AND '.join(f'p.err_{band} BETWEEN 0 AND {MAX_MAGERR}' for band in 'griz')
    fields = ', '.join(f'p.{field}' for field in ['ra', 'dec'] + list(SDSS_TO_REFCAT2_COLUMNS.keys()))

    return (f'SELECT {fields} FROM PhotoObj AS p WHERE p.type = 6 AND {racondition} '
            f'AND p.dec BETWEEN {decmin:.6f} AND {decmax:.6f} AND {errcondition}')


def _query_skyserver(sql, timeout=120):
    """ Run a SQL query against SkyServer and return the result as a Table (empty if no matches).

    Responses are not cached: SkyServer's throttling error page comes back with HTTP 200, and astroquery would
    otherwise cache it and keep returning it for the same query long after the server is available again.
    """
    response = SDSS.query_sql_async(sql, timeout=timeout, cache=False)
    response.raise_for_status()
    text = response.text
    if text.lstrip().lower().startswith('<html') or 'Forbidden' in text[:2000]:
        raise SkyServerRefusedError("SkyServer refused the request (likely throttling anonymous clients)")
    return Table.read(text, format='ascii.csv', comment='#')


def get_reference_catalog(ra, dec, width=30):
    """
    Query the SDSS photometric catalog for stars in a rectangular region centered on (ra, dec).

    :param ra: Right ascension of the field center, in degrees.
    :param dec: Declination of the field center, in degrees.
    :param width: Width (and height) of the rectangular search box, in arcminutes. Defaults to 30.
    :return: astropy.table.Table with columns ra, dec, umag, umagerr, gmag, gmagerr, rmag, rmagerr,
             imag, imagerr, zmag, zmagerr, compatible with the table returned by
             atlasrefcat2.atlas_refcat2.get_reference_catalog. Returns None on failure or no matches.
    """
    try:
        result = _query_skyserver(_build_query(ra, dec, width))
    except SkyServerRefusedError as e:
        _logger.error(f"{e}; no reference catalog for ra={ra}, dec={dec}")
        return None
    except Exception as e:
        _logger.exception(f"While querying SDSS photometric catalog: {e}")
        return None

    if len(result) == 0:
        _logger.warning(f"SDSS query returned no sources for ra={ra}, dec={dec}, width={width} arcmin")
        return None

    table = Table()
    table['ra'] = np.array(result['ra'], dtype=np.float32)
    table['dec'] = np.array(result['dec'], dtype=np.float32)
    for sdss_name, refcat2_name in SDSS_TO_REFCAT2_COLUMNS.items():
        table[refcat2_name] = np.array(result[sdss_name], dtype=np.float32)

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
