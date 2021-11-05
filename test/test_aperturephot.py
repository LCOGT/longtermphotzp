import astropy.io.fits as fits
import os.path
import longtermphotzp.aperturephot as apphot

def do_aperturephot(filename,ap,ri,ro):
    f = fits.open(filename)
    catalog = f['CAT'].data
    image = f['SCI'].data
    apphot.redoAperturePhotometry(catalog, image, ap,ri,ro)


def test_aperturephot():
    startdir = os.path.dirname(os.path.abspath(__file__))

    do_aperturephot(f"{startdir}/data/lsc0m412-kb26-20211102-0100-e91.fits.fz", 10,12,14)


test_aperturephot()