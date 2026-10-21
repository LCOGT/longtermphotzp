# Changelog

Unreleased
* Site specific atmospheric extinction (airmass) terms for the throughput trend model, fitted from all fa (1m),
  sq (0.4m) and ep cameras of each site over Oct 2025 - Oct 2026. Sites / filters without a reliable fit fall back to the
  per-filter default.
* Per-filter default extinction updated to the median over sites: B 0.23 -> 0.266, gp 0.14 -> 0.185,
  V 0.12 -> 0.134, rp 0.08 -> 0.084, ip 0.06 -> 0.054, zs and zp 0.04 -> 0.025 mag/airmass.
  Airmass-corrected zeropoints and stored throughput models change accordingly; for gp by up to ~0.06 mag at
  airmass 2.
* New analysis scripts `airmassterms` and `colorterms` with camera type selection (`--camera-types ep fa sq`).
* Do not fail when no color terms were measured (e.g. a telescope id without data).

Version 8.3.0

**Change in the photometry measurement (photcalibration).** Zeropoints from this version are not
directly comparable with earlier ones at the level of a few hundredths of a magnitude (see below).

* Stellar fluxes are now taken from BANZAI's fixed circular aperture `fluxaper6` (6" diameter) instead of
  the adaptive Kron aperture `flux`. The Kron aperture shrinks for faint stars and measures them too faint:
  on the test images the zeropoint residual drifted by -5 to -18 mmag per magnitude of stellar brightness.
  With the fixed aperture this trend is reduced to 0 to -6 mmag/mag.
* A fixed aperture misses a seeing- and focus-dependent fraction of the starlight (0 - 30 % on the test
  images). Each image therefore gets an aperture correction: the median Kron / `fluxaper6` flux ratio of the
  brightest quarter of the unsaturated, unflagged stars, where the Kron aperture collects nearly all the
  light. The zeropoint stays on the total-flux scale and does not depend on seeing. The correction is shown
  in the title of the zeropoint diagnostic plot.
* Effect on the test images:
  * zeropoints change by at most 0.035 mag,
  * the star-to-star zeropoint scatter (`zpsig`) is about halved for most images,
  * colour terms no longer absorb the magnitude-dependent bias of the Kron photometry
    (e.g. elp 1m B: -0.093 -> -0.034).
* Measurements in the database made with earlier versions used the Kron flux. Mixed old and new
  measurements can differ by up to ~0.035 mag per image until older data are reprocessed.
* Catalogs re-measured with `--fromraw` or `--aperturephot` keep using their own `FLUX` column, as before.

Throughput trend model (photzptrends)
* Fixed upper-envelope fit: the brightest instead of the faintest measurement of a night is rejected as
  outlier; the median filter no longer pads with zeros, which biased the most recent model points low;
  nights are split at local noon of the site instead of 12 UTC; NaN checks work.
* Correct zeropoints of all 0.4m QHY (sq) cameras between 2026-04-08 and 2026-05-05, when their gain was
  misconfigured by a factor of 2 (zeropoints were 0.75 mag too bright).
* Mirror wash / maintenance dates refined from steps in the zeropoint data (27 dates), and 28 events
  detected in the data added.

Other changes since 8.2.1
* Centralized logging configuration, decluttered logging.
* Stricter error margins and fit error rejection; option to query the SDSS catalog directly.
* Fix for crawldirectory table mismatch.

Version 8.1.17
* remove kb, fs cameras from crawler as they are no longer used at LCO

Version 8.1.16
* fix Muscat narrow band association
* .gitignore cleanup

Version 8.1.15
* update mirror wash / delta rho installation dates.

Version 8.1.14
* revert to python 3.10 image

Version 8.1.13
* version number synchronisation

Version 8.1.12
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

