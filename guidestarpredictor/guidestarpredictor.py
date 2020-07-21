import longtermphotzp.atlasrefcat2 as atlas
import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord, Galactic, ICRS


def get_FOV_needed_for_position (ra = 0, dec=0, database = None, maglimit=17, initradius=20*60 / 3600. ):
    starlist = database.get_reference_catalog(ra,dec,initradius)
    starlist = starlist [ starlist['r'] < maglimit]
    if (len(starlist) == 0):
        print ("Nothing!")
        return None
    cReference = SkyCoord(ra=starlist['RA'] * u.degree, dec=starlist['DEC'] * u.degree)
    refposition = SkyCoord (ra * u.degree, dec * u.degree)
    seperations = cReference.separation(refposition).to(u.arcsec)
    angles = cReference.position_angle(refposition).to(u.deg)

    closestidx = np.argmin (seperations)
    return seperations[closestidx] / u.arcsec, angles[closestidx] / u.deg,



def galacticgrid (database):

    galcoo = []
    seperation = []

    f = open ("guidestargrid_r17.txt", "w")



    for l in np.arange (0, 360,1):
        for b in np.arange (-90,91,1):
            galcoo = Galactic (l=l*u.degree, b=b*u.degree)
            radec = galcoo.transform_to(ICRS())

            distance, angle = get_FOV_needed_for_position(ra=radec.ra / u.degree, dec=radec.dec / u.degree, database=database)
            print (radec, distance)
            if distance is not None:
                f.write (f'{radec.ra / u.degree} {radec.dec / u.degree} {distance} {angle} \n' )
                f.flush()
    f.close()







def main():
    atlasdb = atlas.atlas_refcat2 ('/Catalogs/refcat2/refcat2.db')
    galacticgrid(atlasdb)
    pass

if __name__ == '__main__':
    main()

