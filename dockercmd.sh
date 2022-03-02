docker run  \
    -e ARCHIVE_API_TOKEN=$ARCHIVE_API_TOKEN \
    -e DATABASE=$DATABASE \
    -v `pwd`/issue1595:/output \
    -a STDOUT \
    -a STDERR \
    photzp \
    photcalibration  --diagnosticplotsdir /output/ --useaws --lastNdays 600 --mintexp 59 --camera fa20 --filters  V   --photodb $DATABASE
    
