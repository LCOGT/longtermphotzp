import datetime
import logging
import os.path

import sep

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


def fitmerritfunction(x, imageobject, matchedcatlog, fwhm, pngname=None):
    ''' x: vector of paramters
        inputimage: pixel array
        inputcatlog: list of sources where to to photometry.
        '''

    z = x[0] * 1000
    k = x[1]
    zk = z**k
    assert (z>=0)
    assert (k>=0.5)
    rectifieddata = imageobject['SCI'].data.astype(float)
    rectifieddata[rectifieddata<0] = 0
    rectifieddata = (rectifieddata  + z) ** k - zk
    rectifieddata[rectifieddata < 0] = 0
    rectifieddata = rectifieddata ** (1 / k)


    redo_phot_on_matched_catalog(rectifieddata, matchedcatlog, [9,10,15])
    #redo_phot_on_matched_catalog(rectifieddata, matchedcatlog, [12,15,20])

    brightest = np.min(matchedcatlog['refmag'])

    zp = matchedcatlog['refmag'] - matchedcatlog['instmag']
    nbrightest = (matchedcatlog['refmag'] - brightest < 4)# & (np.abs (zp) - np.nanmedian (zp) < 1) & (matchedcatlog['refmag'] > 12)
    myzp = np.nanmedian(zp[nbrightest])
    deviation = np.nanstd (zp[nbrightest]-myzp)

    selzp = zp[nbrightest]
    selref = matchedcatlog['refmag'][nbrightest]

    f=np.polyfit (selref,selzp,1)
    p = np.poly1d(f)
    delta = np.abs (selzp - p(selref))
    cond = (delta < 0.3) & (delta < 3*np.std(delta))
    f = np.polyfit(selref[cond], selzp[cond],1)
    p = np.poly1d(f)

    _logger.debug(f"{x} -> {myzp} +/- {f[0]}")

    if pngname is not None:
        plt.figure()
        plt.plot(matchedcatlog['refmag'], zp, ".", c='grey')
        plt.plot(matchedcatlog['refmag'][nbrightest], zp[nbrightest], '.')
        x = np.arange(10,20)
        plt.plot (x,p(x))
        plt.ylim([myzp-1, myzp+1])
        plt.axhline(myzp)
        plt.xlabel ("reference magnitude")
        plt.ylabel ('reference mag - instrument mag')

        plt.title (f"{pngname}\nk = {k:5.3f} z = {z:5.2f}  zp = {myzp:5.2f} ")
        plt.savefig(pngname, bbox_inches='tight')
        plt.close()

    return np.abs (f[0])


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

    def __init__(self, imageobject, photcalib=None, pngstart=None):
        self.imageobject = imageobject
        self.photcalib = PhotCalib('http://phot-catalog.lco.gtn/') if photcalib is None else photcalib
        self.matchedcatalog = self.photcalib.generateCrossmatchedCatalog(imageobject, mintexp=1)

        fwhm = self.matchedcatalog['FWHM']
        print (fwhm)

        x0 = [0.3, 1.05]
        bounds = ((0., 5.), ( 1., 3.))

        if pngstart is not None:
            fitmerritfunction((0,1), self.imageobject,self.matchedcatalog,fwhm,pngname=f"{pngstart}_before.png")
        result = scipy.optimize.minimize(fitmerritfunction, x0, (self.imageobject, self.matchedcatalog,fwhm),
                                         bounds=bounds, method='SLSQP', options={'eps':0.05})
        #result = scipy.optimize.brute(fitmerritfunction, ((0,5), (1.,2.)), (self.imageobject, self.matchedcatalog),
                                         #)

        print(f"Fitting result:\n{result}")
        if pngstart is not None:
            fitmerritfunction(result.x, self.imageobject,self.matchedcatalog,fwhm,pngname=f"{pngstart}_after.png")

def test_fit(image):
    imageobject = fits.open(image)
    f = SingleLinearityFitter(imageobject, pngstart=os.path.basename(image))




logging.basicConfig(level=getattr(logging, 'INFO'),
                    format='%(asctime)s.%(msecs).03d %(levelname)7s: %(module)20s: %(message)s')

#test_fit("test/data/tfn0m414-kb95-20211116-0030-e91.fits.fz")
#test_fit("test/data/tfn0m414-kb95-20211116-0032-e91.fits.fz")
#test_fit("test/data/tfn0m414-kb95-20211116-0033-e91.fits.fz")
#test_fit("test/data/cpt0m407-kb87-20211109-0027-e91.fits.fz")
#test_fit("test/data/lsc0m409-kb96-20191208-0207-e91.fits.fz" )
test_fit ("test/data/cpt1m012-fa06-20200113-0102-e91.fits.fz")