import argparse
import datetime
import logging
import os

import numpy as np

import longtermphotzp.es_aws_imagefinder as es_aws_imagefinder
from longtermphotzp.sbiglinearityfit.sbigfitter import fit_singleimage, SingleLinearityFitter
from longtermphotzp.sbiglinearityfit.sbiglinedbinterface import sbiglininterface

_logger = logging.getLogger(__name__)

for _ in ("base", "elasticsearch", "urllib3"):
    logging.getLogger(_).setLevel(logging.CRITICAL)


def parseCommandLine():
    """ Read command line parameters
    """

    parser = argparse.ArgumentParser(
        description='Determine nonlinearity in sbig data')

    parser.add_argument('--log-level', dest='log_level', default='INFO', choices=['DEBUG', 'INFO'],
                        help='Set the log level')

    parser.add_argument('--database', dest='database', default=f'sqlite:///{os.path.expanduser("~/sbiglinearity.db")}',
                        help='Result output directory. .db file is written here')
    parser.add_argument('--imagerootdir', dest='rootdir', default='/archive/engineering',
                        help="LCO archive root directory")
    parser.add_argument('--png', default=None, help="Directory for diagnostic png plots")
    parser.add_argument('--site', dest='site', default=None, help='sites code for camera')
    parser.add_argument('--mintexp', default=10, type=float, help='Minimum exposure time to accept')
    parser.add_argument('--object', default=None, type=str, help='filter for OBJECT name, e.g., "auto focus"')
    parser.add_argument('--maxtexp', default=None, type=float, help='Maximumexposure time to accept')
    parser.add_argument('--redo', action='store_true')
    parser.add_argument('--useaws', action='store_true',
                        help="Use LCO archive API to retrieve frame vs direct /archive file mount access")
    mutex = parser.add_mutually_exclusive_group()
    mutex.add_argument('--date', dest='date', default=[None, ], nargs='+', help='Specific date to process.')
    mutex.add_argument('--lastNdays', type=int)

    cameragroup = parser.add_mutually_exclusive_group()
    cameragroup.add_argument('--camera', dest='camera', default=None, help='specific camera to process. ')
    cameragroup.add_argument('--singlefile', default=None, type=str,
                             help="process a single file on file system")

    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper()),
                        format='%(asctime)s.%(msecs).03d %(levelname)7s: %(module)20s: %(message)s')

    if args.png is not None:
        args.png = os.path.expanduser(args.png)
        print(f"Writing images to  {args.png}")

    if args.singlefile is not None:
        args.singlefile = os.path.expanduser(args.singlefile)

    if (args.lastNdays is not None):
        args.date = []
        today = datetime.datetime.utcnow()
        for ii in range(args.lastNdays):
            day = today - datetime.timedelta(days=ii)
            args.date.append(day.strftime("%Y%m%d"))
        args.date = args.date[::-1]
    return args


def awsprocessimage(image, storageengine, outputdirectory=None):
    filename = str(image['filename'])
    frameid = int(image['frameid'])
    imageName = os.path.basename(filename)
    _logger.info(f'\n\nImage {filename} {frameid} iamgeName for DB is {imageName}\n\n')
    try:
        imageobject = es_aws_imagefinder.download_from_archive(frameid)
    except:
        _logger.exception(f"Error while downloading image {filename} {frameid}")
        return

    pngbasename = os.path.join(outputdirectory, os.path.basename(filename)) if outputdirectory is not None else None

    assert (imageobject is not None)
    f = SingleLinearityFitter(imageobject, pngstart=pngbasename, storageengine=storageengine)


def crawlsinglecamera(args, storageengine):
    if args.site is not None:
        sites = [site for site in args.site.split(',')]
    else:
        sites = ('lsc', 'cpt', 'ogg', 'coj', 'tfn', 'elp')
    for date in args.date:
        for site in sites:

            inputlist = es_aws_imagefinder.get_frames_for_photometry(date, site, camera=args.camera, object=args.object,
                                                                     mintexp=args.mintexp, maxtexp=args.maxtexp)

            _logger.info(f"Found {len(inputlist)} input images from site {site} date {date}")
            # Remove images that were already processed since that would be lame to redo.
            if not args.redo:
                _logger.info("removing duplicates")
                rejects = []
                for image in inputlist['filename']:
                    if storageengine.exists((image[0:-8]).replace('e91', 'e00')):
                        rejects.append(image)

                for r in rejects:
                    row = np.where(inputlist['filename'] == r)
                    if len(row) > 0:
                        row = row[0][0]
                        inputlist.remove_row(row)
            for image in inputlist:
                awsprocessimage(image, storageengine, outputdirectory=args.png)


def sbigmain():
    args = parseCommandLine()

    storageengine = sbiglininterface(args.database)

    if args.singlefile:
        try:
            fit_singleimage(args.singlefile, outputdirectory=args.png, storageengine=storageengine)
        except:
            _logger.exception(f"Somthing went wrong while processing file {args.singlefile} ")

    if args.camera:
        # Yay baby, we are looking for all images from a single camera
        crawlsinglecamera(args, storageengine=storageengine)

    storageengine.close()


if __name__ == '__main__':
    sbigmain()
