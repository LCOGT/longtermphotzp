import longtermphotzp.photcalibration as photcal
import math
from astropy.table import Table
import numpy as np
import os.path

def test_photcalibration():

    input = np.asarray(["./test/data/cpt1m012-fa06-20200113-0102-e91.fits.fz", -1])
    t = Table (input, names=['filename','frameid'])

    p = photcal.PhotCalib(os.path.expanduser('~/Catalogs/refcat2/refcat2.db'))
    photzp, photzpsig, colorterm = p.analyzeImage(t, useaws=False, outputimageRootDir="./test/")
    print (photzp, photzpsig, colorterm)

    assert math.fabs (photzp -23.09) < 0.1, "Test for correct photomertic zeropoint"
    assert math.fabs (colorterm - -0.008) < 0.01, "Test for correct photomertic zeropoint"