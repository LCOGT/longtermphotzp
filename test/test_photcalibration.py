import longtermphotzp.photcalibration as photcal
import math
from astropy.table import Table
import os.path

REFCAT2_URL = 'http://phot-catalog.lco.gtn/'

def do_photometrytestonFile(filename, reference_photzp, reference_colorterm, tmpdir):
    t = Table ([[filename],[-1],], names=['filename','frameid'])
    p = photcal.PhotCalib(REFCAT2_URL)
    for r in t:
        photzp, photzpsig, colorterm = p.analyzeImage(r, useaws=False, outputimageRootDir=tmpdir, mintexp=0)
        print (filename, photzp, photzpsig, colorterm)

    assert math.fabs (photzp - reference_photzp) < 0.1, f"Test for correct photomertic zeropoint of {filename}"
    assert math.fabs (colorterm - reference_colorterm) < 0.01, f"Test for correct colorterm of {filename}"

def test_photcalibration(tmpdir):

    print ("Data are stored in temp dir: ", tmpdir )
    startdir = os.path.dirname(os.path.abspath(__file__))

    do_photometrytestonFile(f"{startdir}/data/cpt1m012-fa06-20200113-0102-e91.fits.fz", 23.1,-0.008, tmpdir=tmpdir)
    do_photometrytestonFile(f"{startdir}/data/ogg2m001-ep04-20201006-0097-e91.fits.fz", 25.13, 0.088, tmpdir=tmpdir)

    ### extrapolated u band
    do_photometrytestonFile(f"{startdir}/data/ogg0m404-kb82-20220413-0070-s91.fits.fz", 16.11, 1.6, tmpdir=tmpdir)

    ### Johnson Cousins filters:
    do_photometrytestonFile(f"{startdir}/data/elp1m008-fa05-20200130-0083-e91.fits.fz", 22.93, -0.247, tmpdir=tmpdir)
    do_photometrytestonFile(f"{startdir}/data/elp1m008-fa05-20200130-0084-e91.fits.fz", 23.25, 0.442, tmpdir=tmpdir)
