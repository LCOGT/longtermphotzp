

import sys
from astropy.table import Table
from matplotlib import pyplot as plt
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy import units as u
from astropy.coordinates import SkyCoord
import logging

from longtermphotzp.logging_config import setup_logging
from longtermphotzp.photcalibration import PhotCalib

_logger = logging.getLogger(__name__)





def matchCatlogs(files):
    """Perform aperture photometry and match the same sources between images.
  
    """
    if not files or len(files) < 2:
        raise ValueError("at least two FITS files are required")
    pc = PhotCalib(None)
    imageobjects = [fits.open(f) for f in files]
    imageSourceCatalogs = [ pc.loadInstrumentalCatalog(f) for f in imageobjects ]
    [f.close() for f in imageobjects]

    matchedCatalog = {}

    for catalogindex in range(len(imageSourceCatalogs)):
        header, catalog = imageSourceCatalogs[catalogindex]
        good = catalog['FLUX'] > 0
        catalog = Table(catalog[good])
        exptime = header['EXPTIME']
        _logger.info(f'Processing catalog Texp={exptime}: {header["ORIGNAME"]}')  
        catalog['mag'] = -2.5 * np.log10(catalog['flux'] / exptime)

        if header['WCSERR'] != 0:
            _logger.info(f"WCS solve not valid in FITS header. Skipping. Error code is: {header['WCSERR']}")
            return None
        else:
            image_wcs = WCS(header)
            catalog['ra'], catalog['dec'] = image_wcs.all_pix2world(catalog['x'], catalog['y'], 1)
        # python crater new loal instances of the catalog, need to write it back to original array....
        imageSourceCatalogs[catalogindex] = (header, catalog)

    # at this time we have catalogs in ra / dec with real magnitudes associated
    
    
    # Start the catalog matching, using astropy skycoords built-in functions.
    refheader, refcatalog = imageSourceCatalogs[0]
    cReference = SkyCoord(ra=refcatalog['ra'] * u.degree, dec=refcatalog['dec'] * u.degree)
    matchedCatalog[refheader['ORIGNAME']] = (refheader,refcatalog)
    
    for (header, catalog) in imageSourceCatalogs[1:]:
        _logger.info(f'Matching catalog : {header["ORIGNAME"]}')
        cNextCatalog = SkyCoord(ra=catalog['ra'] * u.degree, dec=catalog['dec'] * u.degree)    
        idx, d2d, d3d = cReference.match_to_catalog_sky(cNextCatalog)
    
        # Reshuffle the source catalog to index-match the reference catalog.
        # There is probably as smarter way of doing this!
        catalog = np.transpose(catalog)[idx]
        catalog = Table(np.transpose(catalog))   
        distance = cReference.separation(cNextCatalog[idx]).arcsecond
        catalog['dist'] = distance
        print("Matches found: ", len(catalog['dist'][catalog['dist'] < 2]))
        catalog['mag'][catalog['dist'] >= 2] = np.nan
        matchedCatalog[header['ORIGNAME']] = (header, catalog)

    return matchedCatalog

def analyse_linearity(matchedCatalogs):


    plt.figure()

    indices = matchedCatalogs.keys()
    for starIndex in range(len(matchedCatalogs[list(indices)[0]][1])):
        exptimes = []
        magnitudes = []
        for index in indices:
            exptimes.append(matchedCatalogs[index][0]['EXPTIME'])
            magnitudes.append(matchedCatalogs[index][1]['mag'][starIndex])
        if np.isfinite(magnitudes).all():
            plt.plot(        
                exptimes,
                magnitudes, '-'
            
            )
    plt.xlabel('EXPTIME')
    plt.ylabel('Magnitude')
    
    plt.savefig('int_linearity.pdf', dpi=600)
    



    
 

def main():
    setup_logging(level="DEBUG")

    files = sys.argv[1:]
    results = matchCatlogs(files)
    analyse_linearity (results)
    return results


if __name__ == "__main__":
    main()
