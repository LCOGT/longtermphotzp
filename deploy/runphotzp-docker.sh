#!/bin/bash
#TODO:
# 1. command line paramters as docker defined ENV variables

echo "Hello photzp `date`"
cd /lco/throughput/

# TODO: populate via DOCKER
sqlfile="/database/lcophotzp.db"

#printf %s\\n {fl,fa,fs,kb} |  xargs -n 1 -P 3 /usr/local/bin/python3 photcalibration.py --photodb $sqlfile --ps1dir /panstarrs --mintexp 10 --lastNdays 3 --cameratype

photcalibration --photodb $sqlfile --refcat2db /refcat2/refcat2.db --mintexp 10 --lastNdays 3 --cameratype fa
photcalibration --photodb $sqlfile --refcat2db /refcat2/refcat2.db --mintexp 10 --lastNdays 3 --cameratype fs
photcalibration --photodb $sqlfile --refcat2db /refcat2/refcat2.db --mintexp 10 --lastNdays 3 --cameratype kb

longtermphotzp --database $sqlfile --outputdirectory /database --filter gp
longtermphotzp --database $sqlfile --outputdirectory /database --filter rp
longtermphotzp --database $sqlfile --outputdirectory /database --filter ip
longtermphotzp --database $sqlfile --outputdirectory /database --filter zp