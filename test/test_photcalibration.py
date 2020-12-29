import longtermphotzp.photcalibration as photcal
import math
from astropy.table import Table
import os.path


def do_photometrytestonFile(filename, reference_photzp, reference_colorterm, tmpdir):
    t = Table ([[filename],[-1],], names=['filename','frameid'])
    p = photcal.PhotCalib(os.path.expanduser('/Catalogs/refcat2/refcat2.db'))
    for r in t:
        photzp, photzpsig, colorterm = p.analyzeImage(r, useaws=False, outputimageRootDir=tmpdir)
        print (filename, photzp, photzpsig, colorterm)

    assert math.fabs (photzp - reference_photzp) < 0.1, "Test for correct photomertic zeropoint"
    assert math.fabs (colorterm - reference_colorterm) < 0.01, "Test for correct photomertic zeropoint"

def test_photcalibration(tmpdir):

    print ("Data are stored in temp dir: ", tmpdir )
    startdir = os.path.dirname(os.path.abspath(__file__))

    do_photometrytestonFile(f"{startdir}/data/cpt1m012-fa06-20200113-0102-e91.fits.fz", 23.09,-0.008, tmpdir=tmpdir)
    do_photometrytestonFile(f"{startdir}/data/ogg2m001-ep04-20201006-0097-e91.fits.fz", 25.21,-0.0063, tmpdir=tmpdir)

