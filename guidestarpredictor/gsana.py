import math

import matplotlib.pyplot as plt
import numpy as np
from astropy.wcs import WCS
from astropy.io import fits
from astropy.utils.data import get_pkg_data_filename
from astropy.visualization.wcsaxes.frame import EllipticalFrame
from matplotlib import patheffects
from astropy import units as u
from astropy.coordinates import SkyCoord, Galactic, ICRS


def readfile (file):
    data = np.loadtxt (file).T
    ## Distribution of distance to guide star
    print (f"Min / max angles: {np.min (data[3])} {np.max(data[3])} ")
    x = np.abs (data[2] * np.cos (data[3] * math.pi/180))
    y = np.abs (data[2] * np.sin (data[3] * math.pi/180))
    minsquare = np.maximum (x,y)
    print (len(x))

    return (data, minsquare)



n_bins=100
data17, minsquare17 = readfile ('guidestargrid_r17.txt')
data18, minsquare18 = readfile ('guidestargrid_r18.txt')

n,bins, patches = plt.hist (minsquare17, n_bins, density=True, histtype = 'step', cumulative=True, label="min. square to r=17 (S/N=50) mag star")
n,bins, patches = plt.hist (minsquare18, n_bins, density=True, histtype = 'step', cumulative=True, label="min. square to r=18 (S/n=20) mag star")
plt.xlabel("Distance viable gudie star to reference position")
plt.ylabel ("Frequency")
plt.legend(loc=4)
plt.savefig ("guidestarshisto.png")

eq = SkyCoord(data18[0], data18[1], unit=u.deg)

ax = plt.subplot(111, projection='aitoff')
plt.grid(True)
plt.plot(eq.ra.wrap_at('180d').deg * math.pi/180., eq.dec.deg * math.pi/180., ',')

plt.savefig ("ProbedGrid.png", dpi=300)
