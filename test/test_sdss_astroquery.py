import matplotlib

matplotlib.use('Agg')
from matplotlib import pyplot as plt
from astropy.coordinates import Longitude
from astropy import units as u

import longtermphotzp.sdss_astroquery as sdss_astroquery


def test_get_reference_catalog_plot(tmpdir):
    print (tmpdir)
    cat = sdss_astroquery.get_reference_catalog(ra=0, dec=0, width=30)

    assert cat is not None
    assert len(cat) > 0
    assert 'ra' in cat.columns
    assert 'dec' in cat.columns

    # wrap RA at 180 deg so sources straddling the 0/360 boundary stay contiguous
    ra_wrapped = Longitude(cat['ra'], unit=u.deg).wrap_at(180 * u.deg).deg

    plt.figure()
    plt.scatter(ra_wrapped, cat['dec'], s=2)
    plt.xlabel('RA [deg]')
    plt.ylabel('Dec [deg]')
    plt.title('SDSS sources around RA=0, Dec=0')
    plt.savefig(f"{tmpdir}/sdss_sources.png")
    plt.close()
