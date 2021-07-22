import math
import os
import requests

import numpy as np
from astropy.table import Table
import logging
_logger = logging.getLogger(__name__)


class atlas_refcat2:
    ''' Interface to query consolidated sqlite3 db file that was generated from Tonry (2018) refcat2
    '''

    FILTERMAPPING = {}
    FILTERMAPPING['gp'] = {'refMag': 'gmag', 'colorTerm': 0.0, 'airmassTerm': 0.20, 'defaultZP': 0.0}
    FILTERMAPPING['rp'] = {'refMag': 'rmag', 'colorTerm': 0.0, 'airmassTerm': 0.12, 'defaultZP': 0.0}
    FILTERMAPPING['ip'] = {'refMag': 'imag', 'colorTerm': 0.0, 'airmassTerm': 0.08, 'defaultZP': 0.0}
    FILTERMAPPING['zp'] = {'refMag': 'zmag', 'colorTerm': 0.0, 'airmassTerm': 0.05, 'defaultZP': 0.0}
    FILTERMAPPING['zs'] = {'refMag': 'zmag', 'colorTerm': 0.0, 'airmassTerm': 0.05, 'defaultZP': 0.0}

    ###  PS to SDSS color transformations according to  Finkbeiner 2016
    ###  http://iopscience.iop.org/article/10.3847/0004-637X/822/2/66/meta#apj522061s2-4 Table 2
    ###  Note that this transformation is valid for stars only. For the purpose of photometric
    ###  calibration, it is desirable to select point sources only from the input catalog.

    ## Why reverse the order of the color term entries? Data are entered in the order as they are
    ## shown in paper. Reverse after the fact to avoid confusion when looking at paper

    ps1colorterms = {}
    ps1colorterms['gmag'] = [-0.01808, -0.13595, +0.01941, -0.00183][::-1]
    ps1colorterms['rmag'] = [-0.01836, -0.03577, +0.02612, -0.00558][::-1]
    ps1colorterms['imag'] = [+0.01170, -0.00400, +0.00066, -0.00058][::-1]
    ps1colorterms['zmag'] = [-0.01062, +0.07529, -0.03592, +0.00890][::-1]

    def __init__(self, refcat2_url):
        self.refcat2_url = refcat2_url

    def isInCatalogFootprint(self, ra, dec):
        return True

    def PStoSDSS(self, table):
        """
        Modify table in situ from PS1 to SDSS, requires column names compatible with ps1colorterms definition.

        :param table:
        :return: modified table.
        """
        if table is not None:
            pscolor = table['gmag'] - table['imag']
            for filter in self.ps1colorterms:
                colorcorrection = np.polyval(self.ps1colorterms[filter], pscolor)
                table[filter] -= colorcorrection

        return table

    def get_reference_catalog(self, ra, dec, radius):
        " Read region of interest from the catalog"
        try:
            response = requests.get(self.refcat2_url + 'radius', params={'ra': ra, 'dec': dec, 'radius': radius})
            response.raise_for_status()
            table = Table(response.json())
        except Exception as e:
            _logger.exception(f"While trying to read from refcat2: {e}")
            return None

        table = self.PStoSDSS(table)

        return table
