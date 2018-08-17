Las Cumbres Observatory long term monitoring of telescope throughput
---

This repository hosts the tools to provide a long term telescope throughput monitoring service. The components are:

 * python code to cross-match source catalogs from BANZAI-reduced iamges with the PANSTARRS catalog and derive a photoemtric zeropoint. The zeropoint is written into a database.
 * python code to analyze the content of the zeropoint data base and create a number of plots .
 
 Dependencies:
 * read-only access to LCO archive mount at /archive
 * read-only access to a local copy of the PANSTARRS catalog
   * This is accessible on chanunpa at /net/fsfs.lco.gtn/data/AstroCatalogs/PS1/
 * read/write access to a directory that will contain 
   * The database file itself
   * mirror throughput model files, trend plots (pngs), and a html file gluing it all together. 
   * ideally, this directory is the only one mounted with write permission. goal is to contain write access
   
   
An example way to run a photometric calibration is provided in the deploy/runphotzp.sh script. 

Usage:
===

To calculate the photometric zeropoint of a set of iamges:


```
python3 photcalibration.py -h

usage: photcalibration.py [-h] [--log-level {DEBUG,INFO}] [--ps1dir PS1DIR]
                          [--diagnosticplotsdir OUTPUTIMAGEROOTDIR]
                          [--photodb IMAGEDBPREFIX] [--imagerootdir ROOTDIR]
                          [--site SITE] [--mintexp MINTEXP] [--redo]
                          [--preview] [--date DATE [DATE ...] | --lastNdays
                          LASTNDAYS]
                          [--camera CAMERA | --cameratype {fs,fl,kb} | --crawldirectory CRAWLDIRECTORY]

Determine photometric zeropoint of banzai-reduced LCO imaging data.

optional arguments:
  -h, --help            show this help message and exit
  --log-level {DEBUG,INFO}
                        Set the log level
  --ps1dir PS1DIR       Directory of PS1 catalog
  --diagnosticplotsdir OUTPUTIMAGEROOTDIR
                        Output directory for diagnostic photometry plots. No
                        plots generated if option is omitted. This is a time
                        consuming task.
  --photodb IMAGEDBPREFIX
                        Result output directory. .db file is written here
  --imagerootdir ROOTDIR
                        LCO archive root directory
  --site SITE           sites code for camera
  --mintexp MINTEXP     Minimum exposure time to accept
  --redo
  --preview
  --date DATE [DATE ...]
                        Specific date to process.
  --lastNdays LASTNDAYS
  --camera CAMERA       specific camera to process.
  --cameratype {fs,fl,kb}
                        camera type to process at selected sites to process.
  --crawldirectory CRAWLDIRECTORY
                        process all reduced image in specific directoy

```


To interpret the resulting database:

```python3 longtermphotzp.py -h
   usage: longtermphotzp.py [-h] [--log_level {DEBUG,INFO}]
                            [--outputdirectory IMAGEDBPREFIX]
                            [--database DATABASE] [--site SITE]
                            [--telescope TELESCOPE] [--filter {gp,rp,ip,zp}]
                            [--testdb] [--importold]
   
   Calculate long-term trends in photometric database.
   
   optional arguments:
     -h, --help            show this help message and exit
     --log_level {DEBUG,INFO}
                           Set the debug level
     --outputdirectory IMAGEDBPREFIX
                           Directory containing photometryc databases
     --database DATABASE
     --site SITE           sites code for camera
     --telescope TELESCOPE
                           Telescope id. written inform enclosure-telescope,
                           e.g., "domb-1m0a"
     --filter {gp,rp,ip,zp}
                           Which filter to process.
     --testdb
     --importold
```


Deploying at LCO
===

Building the container:
docker build -t docker.lco.global/photzp .
docker push  docker.lco.global/photzp


Running an example in container:
```
 python3 photcalibration.py --mintexp 10 --lastNdays 3 --cameratype fl --photodb /database/lcophotzp.db --ps1dir /panstarrs/
 python3 longtermphotzp.py --database  /database/lcophotzp.db --outputdirectory /database
```