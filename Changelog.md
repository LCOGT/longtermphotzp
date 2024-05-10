# Changelog
8.1.13
version number synchronisation
8.1.12
* Bugfixes

Version 8.1.7
* Restrict measurements to targets with magerr <= 0.02 to get better results. 

Version 8.1.10
* Bugfix
* Add lsc delta rho addition date

Version 8.1.6
* Python and dependencies update to python3.11

Version 8.1.4
* Added more filters for extrapolation.
* Added new mirror washes / recoating events. 

Version 8.1.0
* Include Jonson Cousins photometry

version 8.0.0
* Switch from ElasticSearch to OpenSearch

version 7.1.5
* Add detailed C02 snow cleaning history from LSC

Version 7.1.4

* Multiple additions to force aperture photometry for debugging camera issues
* Adding TFN mirror cleaning.  

Version 7.1.0
* Use a query to an AWS postgres database instead of a locally mounted refcat2 mysql db.

Version 7.0.4
* Fix matplotlib 3.4 incompatibility w/ python 3.6. Bumping python to 3.7

Version 7.0.3
* Add tfn dome A,B telescopes

Version 7.0.2
* Correct COJ realuminsation to show up at such and not just as mirror clean

Version 7.0.1
*  Include COJ realuminsation in Feb 2021

Version 7.0RC1
* test production release

## Version 6.9.12
* Bug fix

## Version 6.9.11
* Use fitsheaders-alias index for elasticsearch

## Version 6.9.10 October 3 2020
* Expand plot range to include z filter.

## Version 6.9.9 October 3 2020
* Treat zp and zs filter the same in images for now. 

## Version 6.9.8 October 1st 2020
* Fix issue where zs filter names were not recognized. now they are mapped to zp. 
* Minor fixes for muscat. Add Muscat installation date og ogg 2m0a timeline as new mirror event.  

## Version 6.9.7 September 2020
* Add Muscat3 ep cameras to be analysed

## Version 6.9.6 August 2020
* Update mirror washes at elp doma and domb

##Version 6.8 March 2020
* Update mirror washes for cpt and elp

##Version(s) 6.x February 2020

* Major refactoring and code changes to deploy in Amazon cloud via kubernetes.
  * Query image catalog from LCO fitsheader database in OpenSearch
  * Ability to fetch images via LCO archive API instead of local file system mount
  * Serve resulting plots viw web app, serving from Amazon S3 buckets 

##Version 5 Feb 13 2018

* Use Tonry et al (2018) Atlas refcat2 catalog instead of PS1 catalog. This new reference 
  catalog has the advantage of all-sky coverage. 
  
  This version includes a tool to build an r-tree indexed sqlite3 representation of the refcat2 
  catalog - just bring time and disk space.    

##Version 4 Sept 10 2018

* Also crawl for fa cameras (Archon-modified fl cameras)

##Version 3 August 27 2018 

* indicate region of good throughput 
* Fit a slope to zp decay for time between mirror swaps.
* updated CO2 cleaning

##Version 2 August 17 2018

* Store mirror models in a separate database table; no more need for ascii files.

##Version 1  August 14 2018

* Initial release on LCO server infrastructure. Currently, the output can be viewed at  http://photzp.lco.gtn 

