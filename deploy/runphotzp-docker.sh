#!/bin/bash

# PostgreSQL Database Configuration using the LCO standard for database
# connection configuration in containerized projects.
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-lcogt-commissioning}"
DB_USER="${DB_USER:-lcogt-commissioning}"
DB_PASS="${DB_PASS:-undefined}"

NDAYS="${NDAYS:-3}"
export REFCAT2_URL=${REFCAT2_URL:-http://phot-catalog.lco.gtn/}
# SQLAlchemy database connection string
export DATABASE="${DATABASE:-postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}}"
echo $DATABASE

photcalibration --useaws --photodb $DATABASE --refcat2-url $REFCAT2_URL --mintexp 10 --lastNdays $NDAYS --cameratype fa
photcalibration --useaws --photodb $DATABASE --refcat2-url $REFCAT2_URL --mintexp 10 --lastNdays $NDAYS --cameratype fs
photcalibration --useaws --photodb $DATABASE --refcat2-url $REFCAT2_URL --mintexp 10 --lastNdays $NDAYS --cameratype kb
photcalibration --useaws --photodb $DATABASE --refcat2-url $REFCAT2_URL --mintexp 10 --lastNdays $NDAYS --cameratype ep
photcalibration --useaws --photodb $DATABASE --refcat2-url $REFCAT2_URL --mintexp 10 --lastNdays $NDAYS --cameratype sq

longtermphotzp --database $DATABASE --outputdirectory /database --filter up
longtermphotzp --database $DATABASE --outputdirectory /database --filter gp
longtermphotzp --database $DATABASE --outputdirectory /database --filter rp
longtermphotzp --database $DATABASE --outputdirectory /database --filter ip
longtermphotzp --database $DATABASE --outputdirectory /database --filter zp
longtermphotzp --database $DATABASE --outputdirectory /database --filter B
longtermphotzp --database $DATABASE --outputdirectory /database --filter V
longtermphotzp --database $DATABASE --outputdirectory /database --filter Rc
longtermphotzp --database $DATABASE --outputdirectory /database --filter I

# Exit successfully. None of the above commands take success/failure into
# account, so we don't care here either...
exit 0
