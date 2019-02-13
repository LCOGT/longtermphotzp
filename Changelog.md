Version 5 Feb 13 2018
---
* Use Tonry et al (2018) Atlas refcat2 catalog instead of PS1 catalog. This new reference 
  catalog has the advantage of all-sky coverage. 
  
  This version includes a too to build a r-tree indexed sqlite3 representation of the refcat2 
  catalog - just bring time and disk space.    

Version 4 Sept 10 2018
---
* Also crawl for fa cameras (Archon-modified fl cameras)


Version 3 August 27 2018 
---
* indicate region of good throughput 
* Fit a slope to zp decay for time between mirror swaps.
* updated CO2 cleaning


Version 2 August 17 2018
---
Store mirror models in a seperate database table; no more need for ascii files.



Version 1  August 14 2018
---

Initial release on LCO server infrastructure. Currently the output can be viewd at  http://photzp.lco.gtn 

