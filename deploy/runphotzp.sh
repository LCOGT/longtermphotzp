#!/bin/bash

cd ~/Software/lco-throughputreport/src/longtermphotzp

source ../../venv/bin/activate

printf %s\\n {fl,fa,fs,kb} | nice xargs -n 1 -P 3 python3 photcalibration.py --mintexp 10 --lastNdays 3 --cameratype

nice python3 longtermphotzp.py --filter rp
nice python3 longtermphotzp.py --filter gp
cp /home/dharbeck/lcozpplots/index.html /home/dharbeck/lcozpplots/*.png /var/www/html/lcozpplots

