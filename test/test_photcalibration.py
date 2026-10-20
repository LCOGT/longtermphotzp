import longtermphotzp.photcalibration as photcal
import math
from astropy.table import Table
import os.path

REFCAT2_URL = 'http://phot-catalog.lco.gtn/'

def do_photometrytestonFile(filename, reference_photzp, reference_colorterm, tmpdir):
    t = Table ([[filename],[-1],], names=['filename','frameid'])
    p = photcal.PhotCalib(REFCAT2_URL)
    
    photzp, photzpsig, colorterm = p.analyzeImage(t, useaws=False, outputimageRootDir=tmpdir, mintexp=0)
    print (filename, photzp, photzpsig, colorterm)

    assert math.fabs (photzp - reference_photzp) < 0.1, f"Test for correct photomertic zeropoint of {filename}"
    assert math.fabs (colorterm - reference_colorterm) < 0.01, f"Test for correct colorterm of {filename}"

def test_photcalibration(tmpdir):

    print ("Data are stored in temp dir: ", tmpdir )
    startdir = os.path.dirname(os.path.abspath(__file__))

    do_photometrytestonFile(f"{startdir}/data/cpt1m012-fa06-20200113-0102-e91.fits.fz", 23.08, 0.018, tmpdir=tmpdir)
    do_photometrytestonFile(f"{startdir}/data/ogg2m001-ep04-20201006-0097-e91.fits.fz", 25.15, 0.070, tmpdir=tmpdir)

    ### extrapolated u band
    do_photometrytestonFile(f"{startdir}/data/ogg0m404-kb82-20220413-0070-s91.fits.fz", 16.03, 1.828, tmpdir=tmpdir)

    ### Johnson Cousins filters, referenced to the johnson-transformed sdss photometrÏy:
    do_photometrytestonFile(f"{startdir}/data/elp1m008-fa05-20200130-0083-e91.fits.fz", 23.16, -0.034, tmpdir=tmpdir)
    do_photometrytestonFile(f"{startdir}/data/elp1m008-fa05-20200130-0084-e91.fits.fz", 23.27, -0.015, tmpdir=tmpdir)

    ### Delta Rho & QHY600
    do_photometrytestonFile(f"{startdir}/data/ogg0m455-sq30-20240317-0123-e91.fits.fz", 21.00, -0.006, tmpdir=tmpdir)


def test_aperture_correction_from_bright_stars():
    import numpy as np
    n = 40
    flux = np.logspace(3, 6, n)
    catalog = np.rec.fromarrays(
        [flux, flux / 10 ** (0.4 * 0.12), np.full(n, 1000.), np.full(n, 100.), np.zeros(n, dtype=int)],
        names=['flux', photcal.APERTURE_FLUX, 'peak', 'background', 'flag'])
    catalog[photcal.APERTURE_FLUX][:5] = catalog['flux'][:5]  # faint stars must not influence the correction
    catalog['peak'][-1] = 1e6  # saturated star is ignored
    catalog[photcal.APERTURE_FLUX][-1] = 1.
    p = photcal.PhotCalib(REFCAT2_URL)
    apcor = p.apertureCorrection(catalog, np.ones(n, dtype=bool), saturate=1e5)
    assert math.fabs(apcor - 0.12) < 1e-6
    assert p.apertureCorrection(catalog[:3], np.ones(3, dtype=bool), saturate=1e5) is None
