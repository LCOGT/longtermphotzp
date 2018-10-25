#!/bin/bash

cd ~/Software/lco-throughputreport/src/longtermphotzp

source ../../venv/bin/activate

sem -j 1 python3 photcalibration.py --mintexp 10 --lastNdays 3 --cameratype fl
sem -j 1 python3 photcalibration.py --mintexp 10 --lastNdays 3 --cameratype fa
sem -j 1 python3 photcalibration.py --mintexp 10 --lastNdays 3 --cameratype fs
sem -j 1 python3 photcalibration.py --mintexp 10 --lastNdays 3 --cameratype kb

sem wait

nice python3 longtermphotzp.py --filter rp
nice python3 longtermphotzp.py --filter gp
cp /home/dharbeck/lcozpplots/index.html /home/dharbeck/lcozpplots/*.png /var/www/html/lcozpplots

