import math
import os

import numpy
import requests

import numpy as np
from astropy.table import Table
from astroquery.sdss import SDSS
from astropy import coordinates as coords
import logging
_logger = logging.getLogger(__name__)


class atlas_refcat2:
    ''' Interface to query consolidated sqlite3 db file that was generated from Tonry (2018) refcat2
    '''

    FILTERMAPPING = {}
    FILTERMAPPING['up'] = {'refMag': 'umag', 'colorTerm': 0.0, 'airmassTerm': 0.59, 'defaultZP': 0.0}
    FILTERMAPPING['gp'] = {'refMag': 'gmag', 'colorTerm': 0.0, 'airmassTerm': 0.14, 'defaultZP': 0.0}
    FILTERMAPPING['rp'] = {'refMag': 'rmag', 'colorTerm': 0.0, 'airmassTerm': 0.08, 'defaultZP': 0.0}
    FILTERMAPPING['ip'] = {'refMag': 'imag', 'colorTerm': 0.0, 'airmassTerm': 0.06, 'defaultZP': 0.0}
    FILTERMAPPING['zp'] = {'refMag': 'zmag', 'colorTerm': 0.0, 'airmassTerm': 0.04, 'defaultZP': 0.0}
    FILTERMAPPING['zs'] = {'refMag': 'zmag', 'colorTerm': 0.0, 'airmassTerm': 0.04, 'defaultZP': 0.0}
    FILTERMAPPING['Y'] = {'refMag': 'ymag', 'colorTerm': 0.0, 'airmassTerm': 0.03, 'defaultZP': 0.0}
    FILTERMAPPING['U'] = {'refMag':  'U', 'colorTerm': 0.0, 'airmassTerm': 0.54, 'defaultZP': 0.0}
    FILTERMAPPING['B'] = {'refMag':  'B', 'colorTerm': 0.0, 'airmassTerm': 0.23, 'defaultZP': 0.0}
    FILTERMAPPING['V'] = {'refMag':  'V', 'colorTerm': 0.0, 'airmassTerm': 0.12, 'defaultZP': 0.0}
    FILTERMAPPING['R'] = {'refMag':  'R', 'colorTerm': 0.0, 'airmassTerm': 0.09, 'defaultZP': 0.0}
    FILTERMAPPING['Rc'] = {'refMag':  'R', 'colorTerm': 0.0, 'airmassTerm': 0.09, 'defaultZP': 0.0}
    FILTERMAPPING['I'] = {'refMag':  'I', 'colorTerm': 0.0, 'airmassTerm': 0.04, 'defaultZP': 0.0}

    ###  PS to SDSS color transformations according to  Finkbeiner 2016
    ###  http://iopscience.iop.org/article/10.3847/0004-637X/822/2/66/meta#apj522061s2-4 Table 2
    ###  Note that this transformation is valid for stars only. For the purpose of photometric
    ###  calibration, it is desirable to select point sources only from the input catalog.

    ## Why reverse the order of the color term entries? Data are entered in the order as they are
    ## shown in paper. Reverse after the fact to avoid confusion when looking at paper

    ps1colorterms = {}
    ps1colorterms['umag'] = [+0.04438, -2.26095, -0.13387, +0.27099][::-1]
    ps1colorterms['gmag'] = [-0.01808, -0.13595, +0.01941, -0.00183][::-1]
    ps1colorterms['rmag'] = [-0.01836, -0.03577, +0.02612, -0.00558][::-1]
    ps1colorterms['imag'] = [+0.01170, -0.00400, +0.00066, -0.00058][::-1]
    ps1colorterms['zmag'] = [-0.01062, +0.07529, -0.03592, +0.00890][::-1]
    ps1colorterms['ymag'] = [+0.08924, -0.20878, 0.10360,  -0.02441][::-1]
    JohnsonCousin_filters = ['B', 'V', 'R', 'I', 'U']

    def __init__(self, refcat2_url):
        self.refcat2_url = refcat2_url

    def isInCatalogFootprint(self, ra, dec):
        return True

    def SDSS2Johnson (self, table):
        """ Based on Jordi, Grebel, & Ammon 2005  http://www.sdss3.org/dr8/algorithms/sdssUBVRITransform.php
        """

        transformations={}
        # 0 -> sdss base mag
        # 1,2 -> sdss color to use
        # 3 -> color term
        # 4 -> zero point
        transformations['B'] = ['gmag', 'gmag', 'rmag',  0.313,  0.219]
        transformations['V'] = ['gmag', 'gmag', 'rmag', -0.565, -0.016]
        transformations['R'] = ['rmag', 'rmag', 'imag', -0.153, -0.117]
        transformations['I'] = ['imag', 'imag', 'zmag', -0.386, -0.397]
        transformations['U'] = ['B'   , 'umag', 'gmag', +0.79,  -0.93]

        for filter in transformations:
            transformation = transformations[filter]
            table.add_column(numpy.NaN, name=filter)
            table.add_column(numpy.NaN, name=f'{filter}err')
            table[filter] = table [transformation[0]] + (table[transformation[1]] - table[transformation[2]]) * transformation[3] + transformation[4]
            table[f'{filter}err'] = 0
        return table


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
                if filter == "umag":
                    table['umag'] = table['gmag'] - colorcorrection
                    table['umagerr'] = table['gmagerr']
                elif filter == 'ymag':
                    table['ymag'] = table['zmag'] - colorcorrection
                    table['ymagerr'] = table['zmagerr']
                else:
                    table[filter] -= colorcorrection

        return table

    def get_reference_catalog(self, ra, dec, radius, generateJohnson = False):
        " Read region of interest from the catalog"
        try:
            response = requests.get(self.refcat2_url + 'radius', params={'ra': ra, 'dec': dec, 'radius': radius})
            response.raise_for_status()
            table = Table(response.json())
        except Exception as e:
            _logger.exception(f"While trying to read from refcat2: {e}")
            return None

        table = self.PStoSDSS(table)

        if generateJohnson:
            table = self.SDSS2Johnson(table)

        return table
