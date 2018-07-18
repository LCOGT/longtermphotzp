Las Cumbres Observatory long term monitoring of telescope throughput
---

This repository hosts the tools to provide a long term telescope throughput monitoring service. The components are:

 * python code to cross-match source catalogs from BANZAI-reduced iamges with the PANSTARRS catalog and derive a photoemtric zeropoint. The zeropoint is written into a database.
 * python code to analyze the content of the zeropoint data base and create a number of plots .
 
 Dependencies:
 * read access to LCO archive mount at /archive
 * read access to a local copy of the PANSTARRS catalog
 * write access to a directory that will contain 
   * The database file itself
   * mirror throughput model files, trend plots (pngs), and a html file gluing it all together. 