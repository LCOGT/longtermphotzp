#!/bin/bash

cd ~/Software/lco-throughputreport/

source /venv/bin/activate

nice python3 longtermphotzp/photcalibration.py --mintexp 10 --lastNdays 3 --cameratype fa
nice python3 longtermphotzp/photcalibration.py --mintexp 10 --lastNdays 3 --cameratype fs
nice python3 longtermphotzp/photcalibration.py --mintexp 10 --lastNdays 3 --cameratype kb
nice python3 longtermphotzp/photcalibration.py --mintexp 10 --lastNdays 3 --cameratype ep


nice python3 longtermphotzp/longtermphotzp.py --filter rp
nice python3 longtermphotzp/longtermphotzp.py --filter gp

cp /home/dharbeck/lcozpplots/index.html /home/dharbeck/lcozpplots/*.png /var/www/html/lcozpplots

