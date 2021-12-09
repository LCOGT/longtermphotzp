import datetime
import logging

import scipy
from astropy.io import fits
import matplotlib.pyplot as plt
import matplotlib
from astropy.modeling import models, fitting

matplotlib.use('Agg')

import longtermphotzp.aperturephot as aperturephot
import numpy as np
from longtermphotzp.photcalibration import PhotCalib

sqrtfunc = lambda x, gain, z, exp: ((gain * x) ** exp + z ** exp) ** (1 / exp) - z

_logger = logging.getLogger(__name__)

plt.style.use('ggplot')

def redo_phot_on_matched_catalog(imagedata, matchedcatalog, apertures):
    aperturephot.redoAperturePhotometry(matchedcatalog, imagedata, apertures[0], apertures[1], apertures[2])
    matchedcatalog['instmag'] = -2.5 * np.log10(matchedcatalog['FLUX'] / matchedcatalog['exptime'])


def fitmerritfunction(x, imageobject, matchedcatlog):
    ''' x: vector of paramters
        inputimage: pixel array
        inputcatlog: list of sources where to to photometry.
        '''

    z = x[0] * 1000
    k = x[1]
    zk = z**k
    assert (z>=0)
    assert (k>=0.5)
    rectifieddata = imageobject['SCI'].data
    rectifieddata[rectifieddata<0] = 0
    rectifieddata = (rectifieddata  + z) ** k - zk
    rectifieddata[rectifieddata < 0] = 0
    rectifieddata = rectifieddata ** (1 / k)

    redo_phot_on_matched_catalog(rectifieddata, matchedcatlog, [9, 10, 15])

    brightest = np.min(matchedcatlog['refmag'])
    nbrightest = matchedcatlog['refmag'] - brightest < 4
    zp = matchedcatlog['refmag'] - matchedcatlog['instmag']
    myzp = np.nanmean(zp[nbrightest])
    deviation = np.nanstd (zp[nbrightest]-myzp)

    selzp = zp[nbrightest]
    selref = matchedcatlog['refmag'][nbrightest]

    f=np.polyfit (selref,selzp,1)
    p = np.poly1d(f)
    delta = np.abs (selzp - p(selref))
    cond = (delta < 0.2) & (delta < 2*np.std(delta))
    f = np.polyfit(selref[cond], selzp[cond],1)
    p = np.poly1d(f)

    _logger.info(f"{x} -> {myzp} +/- {f}")

    plt.figure()
    plt.plot(matchedcatlog['refmag'], zp, ".", c='grey')
    plt.plot(matchedcatlog['refmag'][nbrightest], zp[nbrightest], '.')
    x = np.arange(10,20)
    plt.plot (x,p(x))
    plt.ylim([20, 23])
    plt.axhline(myzp)

    plt.title (f"k = {k:5.3f} z = {z:5.2f}  zp = {myzp:5.2f} ")
    plt.savefig(f"{datetime.datetime.utcnow()}.png")
    plt.close()

    return f[1]


class SingleLinearityFitter():
    '''Try to bootstrap SBIG non-linearity function based on phtoemtry result.
    Workflow:

    Define merit function: Inputs: Image, targetlist, non-linearity correction function (parameters)

    merit function does:
      (i) create a nonlinear corrected version of the input data
      (ii) run photometry on the input data
      (iii) match input catalog to reference catalog.
      (iv) derive the photometric zeropoint for 3-4 mag brightest stars.
      (iii) calculate and return the rms of the zero point measurement.



    Run scippy.minimizer on this merit function.

    Create optional photzp plot for starting point and  best fit.

    Log best fitting values in a database  for further trend analysis.

    '''

    def __init__(self, imageobject, photcalib=None):
        self.imageobject = imageobject
        self.photcalib = PhotCalib('http://phot-catalog.lco.gtn/') if photcalib is None else photcalib
        self.matchedcatalog = self.photcalib.generateCrossmatchedCatalog(imageobject, mintexp=1)

        x0 = [0.0, 1.0]
        bounds = ((1., 3.), ( 1., 3))
        #result = scipy.optimize.minimize(fitmerritfunction, x0, (self.imageobject, self.matchedcatalog),
            #                             bounds=bounds, method='brute')
        result = scipy.optimize.brute(fitmerritfunction, ((0,5), (1.,2.)), (self.imageobject, self.matchedcatalog),
                                         )

        print(f"Fitting result:\n{result}")


def test_fit(image):
    imageobject = fits.open(image)
    f = SingleLinearityFitter(imageobject)




logging.basicConfig(level=getattr(logging, 'INFO'),
                    format='%(asctime)s.%(msecs).03d %(levelname)7s: %(module)20s: %(message)s')

test_fit("test/data/tfn0m414-kb95-20211116-0030-e91.fits.fz")
#test_fit("test/data/tfn0m414-kb95-20211116-0032-e91.fits.fz")
#test_fit("test/data/tfn0m414-kb95-20211116-0033-e91.fits.fz")
