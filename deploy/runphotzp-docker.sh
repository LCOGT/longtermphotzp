#!/bin/bash

#printf %s\\n {fl,fa,fs,kb} |  xargs -n 1 -P 3 /usr/local/bin/python3 photcalibration.py --photodb $LONGTERMPHOTZP_DATABASE_FILE --ps1dir /panstarrs --mintexp 10 --lastNdays 3 --cameratype

photcalibration --photodb $LONGTERMPHOTZP_DATABASE_FILE --refcat2db $REFCAT2_DATABASE_FILE --mintexp 10 --lastNdays 3 --cameratype fa
photcalibration --photodb $LONGTERMPHOTZP_DATABASE_FILE --refcat2db $REFCAT2_DATABASE_FILE --mintexp 10 --lastNdays 3 --cameratype fs
photcalibration --photodb $LONGTERMPHOTZP_DATABASE_FILE --refcat2db $REFCAT2_DATABASE_FILE --mintexp 10 --lastNdays 3 --cameratype kb

longtermphotzp --database $LONGTERMPHOTZP_DATABASE_FILE --outputdirectory /database --filter gp
longtermphotzp --database $LONGTERMPHOTZP_DATABASE_FILE --outputdirectory /database --filter rp
longtermphotzp --database $LONGTERMPHOTZP_DATABASE_FILE --outputdirectory /database --filter ip
longtermphotzp --database $LONGTERMPHOTZP_DATABASE_FILE --outputdirectory /database --filter zp

# Exit successfully. None of the above commands take success/failure into
# account, so we don't care here either...
exit 0
