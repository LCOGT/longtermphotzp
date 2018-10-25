#!/bin/bash
#TODO:
# 1. command line paramters as docker defined ENV variables

echo "Hello photzp `date`"
cd /lco/throughput/src/longtermphotzp

# TODO: populate via DOCKER
sqlfile="/database/lcophotzp.db"

#printf %s\\n {fl,fa,fs,kb} |  xargs -n 1 -P 3 /usr/local/bin/python3 photcalibration.py --photodb $sqlfile --ps1dir /panstarrs --mintexp 10 --lastNdays 3 --cameratype

sem -j 4 /usr/local/bin/python3 photcalibration.py --photodb $sqlfile --ps1dir /panstarrs --mintexp 10 --lastNdays 3 --cameratype fl
sem -j 4 /usr/local/bin/python3 photcalibration.py --photodb $sqlfile --ps1dir /panstarrs --mintexp 10 --lastNdays 3 --cameratype fa
sem -j 4 /usr/local/bin/python3 photcalibration.py --photodb $sqlfile --ps1dir /panstarrs --mintexp 10 --lastNdays 3 --cameratype fs
sem -j 4 /usr/local/bin/python3 photcalibration.py --photodb $sqlfile --ps1dir /panstarrs --mintexp 10 --lastNdays 3 --cameratype kb

sem wait

/usr/local/bin/python3 longtermphotzp.py --database $sqlfile --outputdirectory /database --filter gp
/usr/local/bin/python3 longtermphotzp.py --database $sqlfile --outputdirectory /database --filter rp