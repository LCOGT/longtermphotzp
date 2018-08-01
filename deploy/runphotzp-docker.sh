#!/bin/bash
#TODO:
# 1. command line paramters as docker defined ENV variables

cd /lco/throughput/src/longtermphotzp

# TODO: populate via DOCKER
sqlfile="/database/lcophotzp.db"

printf %s\\n {fl,fs,kb} |  xargs -n 1 -P 3 python3 photcalibration.py --photodb $sqlfile --ps1dir /panstarrs --mintexp 10 --lastNdays 3 --cameratype

python3 longtermphotzp.py --database $sqlfile --outputdirectory /database --filter rp
python3 longtermphotzp.py --database $sqlfile --outputdirectory /database --filter gp


