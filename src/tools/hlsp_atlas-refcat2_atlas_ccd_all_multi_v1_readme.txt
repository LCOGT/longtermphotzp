README file for ATLAS-REFCAT2 (Tonry et al. 2018) - The ATLAS All-Sky Stellar Reference Catalog
MAST webpage: https://archive.stsci.edu/prepds/atlas-refcat2/index.html
Refer to this HLSP with DOI: http://dx.doi.org/10.17909/t9-2p3r-7651

## Introduction
ATLAS-REFCAT2 is an all-sky reference catalog containing nearly one billion stars down to apparent magnitude m ~19.  The catalog includes PanSTARRS DR1, ATLAS Pathfinder, ATLAS re-flattened APASS, SkyMapper DR1, APASS DR9, Tycho-2, and the Yale Bright Star Catalog.  Gaia DR2 serves as the source of the astrometric solution for ATLAS-REFCAT2, with typical systematic errors of < 5 mmag RMS, although this can be as much as 20 mmag near the Galactic plane.  The ATLAS Pathfinder telescope was used to collect g,r,i photometry for stars brighter than the 14th magnitude bright limit of PanSTARRS, and to extend the reference system below -30 declination.

## Data Products
The ATLAS-REFCAT2 catalog is available in .csv files divided by declintion on the MAST project page.  It is also available in MAST CasJobs (http://mastweb.stsci.edu/mcasjobs/) for SQL access and for cross-matching with numerous other catalogs available at MAST.

### Catalog Columns
Name   |   Data Type   |   Unit   |   Description
-------------------------------------------------
objid      bigint          none       Object ID
RA 	       float  	   degrees    Right ascension from Gaia DR2, J2000, epoch 2015.5
Dec 	   float  	   degrees    Declination from Gaia DR2, J2000, epoch 2015.5
plx 	   real   	   mas	      Parallax from Gaia DR2
dplx 	   real   	   mas	      Parallax uncertainty from Gaia DR2
pmra 	   real   	   mas/yr     Proper motion in right ascension from Gaia DR2
dpmra      real   	   mas/yr     Proper motion uncertainty in right ascension
pmdec      real   	   mas/yr     Proper motion in declination from Gaia DR2
dpmdec     real   	   mas/yr     Proper motion uncertainty in declination
Gaia 	   real   	   mag	      Gaia G magnitude
dGaia      real   	   mag	      Gaia G magnitude uncertainty
BP 	       real   	   mag	      Gaia G_bp magnitude
dBP 	   real   	   mag	      Gaia G_bp magnitude uncertainty
RP 	       real   	   mag	      Gaia G_rp magnitude
dRP 	   real   	   mag	      Gaia G_rp magnitude uncertainty
Teff 	   int    	   K	      Gaia stellar effective temperature
AGaia      real   	   mag	      Gaia estimate of G-band extinction for this star
dupvar     int    	   none	      Gaia variability and duplicate flags, 0/1/2 for "CONSTANT"/"VARIABLE"/"NOT AVAILABLE" + 4*DUPLICATE
Ag 	       real   	   mag	      SFD estimate of total g-band extinction
rp1 	   real   	   arcsec     Radius where cummulative G flux exceeds 0.1 x this star
r1 	       real   	   arcsec     Radius where cummulative G flux exceeds 1.0 x this star
r10 	   real   	   arcsec     Radius where cummulative G flux exceeds 10.0 x this star
g	       real   	   mag	      PanSTARRS g magnitude
dg 	       real   	   mag	      PanSTARRS g magnitude uncertainty
gchi 	   real   	   none	      chi^2 / DOF for contributors
gcontrib   int    	   none	      Bitmap of conributing catalogs to g
r 	       real   	   mag	      PanSTARRS r magnitude
dr 	       real   	   mag	      PanSTARRS r magnitude uncertainty
rchi 	   real   	   none	      chi^2 / DOF for contributors
rcontrib   int    	   none	      Bitmap of conributing catalogs to r
i 	       real   	   mag	      PanSTARRS i magnitude
di 	       real   	   mag	      PanSTARRS i magnitude uncertainty
ichi 	   real   	   none	      chi^2 / DOF for contributors
icontrib   int    	   none	      Bitmap of conributing catalogs to i
z 	       real   	   mag	      PanSTARRS z magnitude
dz 	       real   	   mag	      PanSTARRS z magnitude uncertainty
zchi 	   real   	   none	      chi^2 / DOF for contributors
zcontrib   int    	   none	      Bitmap of conributing catalogs to z
nstat      int    	   none	      Count of griz outliers rejected
J 	       real   	   mag	      2MASS J magnitude
dJ 	       real   	   mag	      2MASS J magnitude uncertainty
H 	       real   	   mag	      2MASS H magnitude
dH 	       real   	   mag	      2MASS H magnitude uncertainty
K 	       real   	   mag	      2MASS K magnitude
dK 	       real   	   mag	      2MASS K magnitude uncertainty

