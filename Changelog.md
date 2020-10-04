# Changelog

## Version 6.9.9 October 3 2020
* Treat zp and zs filter the same in images for now. 

## Version 6.9.8 October 1st 2020
* Fix issue where zs filter names were not recognized. now they are mapped to zp. 
* Minor fixes for muscat. Add Muscat installation date og ogg 2m0a time line as new mirror event.  

## Version 6.9.7 September 2020
* Add Muscat3 ep cameras to be analysed

## Version 6.9.6 August 2020
* Update mirror washes at elp doma and domb

##Version 6.8 March 2020
* Update mirror washes for cpt and elp

##Version(s) 6.x February 2020

* Major refactoring and code changes to deploy in Amazon cloud via kubernetes.
  * Query image catalog from LCO fitshead database in elasticsearch
  * Ability to fetch images via LCO archive API instead of local file system mount
  * Serve resulting plots viw web app, serving from Amazon S3 buckets 

##Version 5 Feb 13 2018

* Use Tonry et al (2018) Atlas refcat2 catalog instead of PS1 catalog. This new reference 
  catalog has the advantage of all-sky coverage. 
  
  This version includes a too to build a r-tree indexed sqlite3 representation of the refcat2 
  catalog - just bring time and disk space.    

##Version 4 Sept 10 2018

* Also crawl for fa cameras (Archon-modified fl cameras)

##Version 3 August 27 2018 

* indicate region of good throughput 
* Fit a slope to zp decay for time between mirror swaps.
* updated CO2 cleaning

##Version 2 August 17 2018

* Store mirror models in a seperate database table; no more need for ascii files.

##Version 1  August 14 2018

* Initial release on LCO server infrastructure. Currently the output can be viewd at  http://photzp.lco.gtn 

