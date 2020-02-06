import astropy
import matplotlib

from longtermphotzp.atlasrefcat2 import atlas_refcat2
from longtermphotzp.photdbinterface import photdbinterface, PhotZPMeasurement
import longtermphotzp.es_aws_imagefinder as es_aws_imagefinder
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.style.use('ggplot')

import numpy as np
import argparse
import re
import glob
import os
import sys
import logging
from astropy.io import fits
from astropy.wcs import WCS
from astropy.table import Table
from astropy.coordinates import SkyCoord
from astropy import units as u
import datetime

_logger = logging.getLogger(__name__)
__author__ = 'dharbeck'


class PhotCalib():
    # To be replaced with map:
    # LCO filter -> sdss filter name, sdsss g-i color term, airmass term, default zero point.
    # possibly need this for all site:telescope:camera:filter settings. Maybe start with one
    # default and see where it goes.
    referencecatalog = None

    def __init__(self, refcat2db):
        self.referencecatalog = atlas_refcat2(refcat2db)

    def do_stage(self, images):
        """ future hook for BANZAI pipeline integration

        """

        for i, image in enumerate(images):
            pass
            # logging_tags = logs.image_config_to_tags(image, self.group_by_keywords)

    def generateCrossmatchedCatalog(self, imageobject, mintexp=60):
        """ Load the banzai-generated photometry catalog from  'CAT' extension, queries PS1 catalog for image FoV, and
        returns a cross-matched catalog.

        Errors conditions:
         if photometric filter is not supported, none is returned
         if exposure time is < 60 seconds, None is returned.

        :param image: an opened fits image
        :return:
        """

        # Build up a baseline refernce catlog with meta data.
        # TODO: this is a bit retarded since we are copying FITS headers around.
        retCatalog = {
            'instmag': None
        }

        # Boilerplate grab of status information
        ra = imageobject['SCI'].header['CRVAL1']
        dec = imageobject['SCI'].header['CRVAL2']

        if not self.referencecatalog.isInCatalogFootprint(ra, dec):
            _logger.debug("Image not in reference catalog footprint. Ignoring")
            return None

        retCatalog['exptime'] = imageobject['SCI'].header['EXPTIME']
        retCatalog['instfilter'] = imageobject['SCI'].header['FILTER']
        retCatalog['airmass'] = imageobject['SCI'].header['AIRMASS']
        retCatalog['dateobs'] = imageobject['SCI'].header['DATE-OBS']
        retCatalog['instrument'] = imageobject['SCI'].header['INSTRUME']
        retCatalog['siteid'] = imageobject['SCI'].header['SITEID']
        retCatalog['domid'] = imageobject['SCI'].header['ENCID']
        retCatalog['telescope'] = imageobject['SCI'].header['TELID']
        retCatalog['FOCOBOFF'] = imageobject['SCI'].header['FOCOBOFF']

        # Check if filter is supported
        if retCatalog['instfilter'] not in self.referencecatalog.FILTERMAPPING:
            _logger.debug(
                "Filter %s not viable for photometric calibration. Sorry" % (retCatalog['instfilter']))
            return None

        # Check if exposure time is long enough
        if (retCatalog['exptime'] < mintexp):
            _logger.debug("Exposure %s time is deemed too short, ignoring" % ( retCatalog['exptime']))
            return None

        # verify there is no deliberate defocus
        if (retCatalog['FOCOBOFF'] is not None) and (retCatalog['FOCOBOFF'] != 0):
            _logger.debug("Exposure is deliberately defocussed by %s, ignoring" % ( retCatalog['FOCOBOFF']))
            return None

        # Get the instrumental filter and the matching reference catalog filter names.
        referenceInformation = self.referencecatalog.FILTERMAPPING[retCatalog['instfilter']]
        referenceFilterName = referenceInformation['refMag']

        # Load photometry catalog from image, and transform into RA/Dec coordinates
        try:
            instCatalog = imageobject['CAT'].data
        except:
            _logger.warning("No extension \'CAT\' available, skipping.")
            return None

        # Transform the image catalog to RA / Dec based on the WCS solution in the header.
        # TODO: rerun astrometry.net with a higher order distortion model

        image_wcs = WCS(imageobject['SCI'].header)
        try:
            ras, decs = image_wcs.all_pix2world(instCatalog['x'], instCatalog['y'], 1)
        except:
            _logger.error("Failed to convert images coordinates to world coordinates. Giving up on file." )
            return None

        # Query reference catalog TODO: paramterize FoV of query!
        refcatalog = self.referencecatalog.get_reference_catalog(ra, dec, 0.25)
        if refcatalog is None:
            _logger.warning("no reference catalog received.")
            return None

        # Start the catalog matching, using astropy skycoords built-in functions.
        cInstrument = SkyCoord(ra=ras * u.degree, dec=decs * u.degree)
        cReference = SkyCoord(ra=refcatalog['RA'] * u.degree, dec=refcatalog['DEC'] * u.degree)
        idx, d2d, d3d = cReference.match_to_catalog_sky(cInstrument)

        # Reshuffle the source catalog to index-match the reference catalog.
        # There is probably as smarter way of doing this!
        instCatalogT = np.transpose(instCatalog)[idx]
        instCatalog = np.transpose(instCatalogT)

        # Measure the distance between matched pairs. Important to down-select viable pairs.
        distance = cReference.separation(cInstrument[idx]).arcsecond

        # Define a reasonable condition on what is a good match on good photometry
        condition = (distance < 5) & (instCatalog['FLUX'] > 0) & (refcatalog[referenceFilterName] > 0) & (
                refcatalog[referenceFilterName] < 26)

        # Calculate instrumental magnitude from PSF instrument photometry
        instmag = -2.5 * np.log10(instCatalog['FLUX'][condition] / retCatalog['exptime'])

        # Calculate the magnitude difference between reference and inst catalog
        retCatalog['instmag'] = instmag
        retCatalog['refcol'] = (refcatalog['g'] - refcatalog['i'])[condition]

        retCatalog['refmag'] = refcatalog[referenceFilterName][condition]
        retCatalog['ra'] = refcatalog['RA'][condition]
        retCatalog['dec'] = refcatalog['DEC'][condition]
        retCatalog['matchDistance'] = distance[condition]
        # TODO: Read photometric error columns from reference and instrument catalogs, properly propagate error.

        return retCatalog

    def reject_outliers(self, data, m=2):
        """
        Reject data from vector that are > m std deviations from median
        :param m:
        :return:
        """
        std = np.std(data)
        return data[abs(data - np.median(data)) < m * std]

    def analyzeImage(self, imageentry, outputdb=None,
                     outputimageRootDir=None, mintexp=60, useaws=False):
        """
            Do full photometric zeropoint analysis on an image. This is the main entry point

            param iamgeentry: Table row to caontain 'filename' and 'frameid'
        """

        # The filename may or may not be the full path to the image

        imageName=os.path.basename(str(imageentry['filename'][0]))

        # Read banzai star catalog
        try:
            if useaws:
                print ("Use AWS")
                imageobject = es_aws_imagefinder.download_from_archive(imageentry['frameid'][0])
            else:
                print ("Loading from file system: {}".format (str(imageentry['filename'][0])))
                imageobject = fits.open(str(imageentry['filename'][0]))
        except:
            _logger.warning ("File {} could not be accessed: {}".format (imageName,sys.exc_info()[0]))
            return None

        retCatalog = self.generateCrossmatchedCatalog(imageobject, mintexp=mintexp)
        imageobject.close()
        if (retCatalog is None) or (retCatalog['instmag'] is None) or (len(retCatalog['ra']) < 10):
            if retCatalog is None:
                return

            if len(retCatalog['ra']) < 10:
                _logger.info("%s: Catalog returned, but is has less than 10 stars. Ignoring. " % (imageentry))
            return

        # calculate the per star zeropoint
        magZP = retCatalog['refmag'] - retCatalog['instmag']
        refmag = retCatalog['refmag']
        refcol = retCatalog['refcol']

        # Calculate the photometric zeropoint.
        # TODO: Robust median w/ rejection, error propagation.

        cleandata = self.reject_outliers(magZP, 3)
        photzp = np.median(cleandata)
        photzpsig = np.std(cleandata)

        # calculate color term

        try:
            cond = (refcol > 0) & (refcol < 3) & (np.abs(magZP - photzp) < 0.75)
            colorparams = np.polyfit(refcol[cond], (magZP - photzp)[cond], 1)
            color_p = np.poly1d(colorparams)
            delta = np.abs(magZP - photzp - color_p(refcol))
            cond = (delta < 0.2)
            colorparams = np.polyfit(refcol[cond], (magZP - photzp)[cond], 1)
            color_p = np.poly1d(colorparams)
            colorterm = colorparams[0]

        except:
            _logger.warning("could not fit a color term. ")
            color_p = None
            colorterm = 0

        # if requested, generate all sorts of diagnostic plots
        if (outputimageRootDir is not None) and (os.path.exists(outputimageRootDir)):
            outbasename = os.path.basename(imageName)
            outbasename = re.sub('.fits.fz', '', outbasename)

            ### Zeropoint plot
            plt.figure()
            plt.plot(refmag, magZP, '.')
            plt.xlim([10, 22])
            plt.ylim([photzp - 0.5, photzp + 0.5])
            plt.axhline(y=photzp, color='r', linestyle='-')
            plt.xlabel("Reference catalog mag")
            plt.ylabel("Reference Mag - Instrumnetal Mag (%s)" % (retCatalog['instfilter']))
            plt.title("Photometric zeropoint %s %5.2f" % (outbasename, photzp))
            plt.savefig("%s/%s_%s_zp.png" % (outputimageRootDir, outbasename, retCatalog['instfilter']))
            plt.close()

            ### Color term plot
            plt.figure()
            plt.plot(refcol, magZP - photzp, '.')
            if color_p is not None:
                xp = np.linspace(-0.5, 3.5, 10)
                plt.plot(xp, color_p(xp), '-', label="color term fit % 6.4f" % (colorterm))
                plt.legend()

            plt.xlim([-0.5, 3.0])
            plt.ylim([-1, 1])
            plt.xlabel("(g-r)$_{\\rm{SDSS}}$ Reference")
            plt.ylabel("Reference Mag - Instrumnetal Mag - ZP (%5.2f) %s" % (photzp, retCatalog['instfilter']))
            plt.title("Color correction %s " % (outbasename))
            plt.savefig("%s/%s_%s_color.png" % (outputimageRootDir, outbasename, retCatalog['instfilter']))
            plt.close()

        if outputdb is not None:
            m = PhotZPMeasurement (name=imageName, dateobs = retCatalog['dateobs'].replace('T', ' '),
                                   site = retCatalog['siteid'], dome = retCatalog['domid'],
                                   telescope=  retCatalog['telescope'], camera = retCatalog['instrument'],
                                   filter = retCatalog['instfilter'], airmass = retCatalog['airmass'],
                                   zp = photzp, colorterm = colorterm, zpsig = photzpsig)
            outputdb.addphotzp(m)
            # outputdb.addphotzp(
            #     (imageName, retCatalog['dateobs'].replace('T', ' '), retCatalog['siteid'], retCatalog['domid'],
            #      retCatalog['telescope'], retCatalog['instrument'], retCatalog['instfilter'],
            #      retCatalog['airmass'], photzp, colorterm, photzpsig))
        else:
            _logger.info("Not saving output for image %s " % imageName)

        return photzp, photzpsig, colorterm


def process_imagelist(inputlist: astropy.table.Table, db, args, rewritetoarchivename=True, inputlistIsArchiveID=False):
    """ Invoke the per image processing for a list of files, but check for duplication. """
    # get list of files of interest from elasticsearch
    initialsize = len(inputlist)
    print(inputlist)
    rejects = []
    if not args.redo:
        for image in inputlist['filename']:
            if db.exists(image):
                rejects.append(image)

        for r in rejects:
            pass
            # TODO: find out how to delete table entries that are duplicate
            row = np.where(inputlist['filename'] == r)
            if len(row)>0:
                row = row[0][0]
                _logger.info (f"remove duplicate from table: {r} at row {row}")
                inputlist.remove_row(row)

            # inputlist.remove(r)
    _logger.debug("Found %d files initially, but cleaned %d already measured images. Starting analysis of %d files" % (
        initialsize, len(rejects), len(inputlist)))

    photzpStage = PhotCalib(args.refcat2db)
    for image in inputlist:
        if rewritetoarchivename:
            fn = lcofilename_to_archivepath(image['filename'], args.rootdir)
            image = Table (np.asarray([fn,image['frameid']]), names=['filename','frameid'])
        print (image)
        photzpStage.analyzeImage(image, outputdb=db, outputimageRootDir=args.outputimageRootDir, mintexp=args.mintexp, useaws=args.useaws)
        _logger.debug("analyze image: {}".format(image))


def lcofilename_to_archivepath(filename, rootpath):
    # _logger.debug ("Finding full apth name for image {} at root {}".format(filename, rootpath))
    m = re.search('^(...).....-(....)-(........)', filename)
    site = m.group(1)
    camera = m.group(2)
    dateobs = m.group(3)

    return "{}/{}/{}/{}/processed/{}".format(rootpath, site, camera, dateobs, filename)


def parseCommandLine():
    """ Read command line parameters
    """

    parser = argparse.ArgumentParser(
        description='Determine photometric zeropoint of banzai-reduced LCO imaging data.')

    parser.add_argument('--log-level', dest='log_level', default='INFO', choices=['DEBUG', 'INFO'],
                        help='Set the log level')
    parser.add_argument('--refcat2db', dest='refcat2db', default='~/Catalogs/refcat2/refcat2.db',
                        help='Directory of Atlas refcat2 catalog database')
    parser.add_argument("--diagnosticplotsdir", dest='outputimageRootDir', default=None,
                        help='Output directory for diagnostic photometry plots. No plots generated if option is omitted. This is a time consuming task. ')
    parser.add_argument('--photodb', dest='imagedbPrefix', default='~/lcozpplots/lcophotzp.db',
                        help='Result output directory. .db file is written here')
    parser.add_argument('--imagerootdir', dest='rootdir', default='/archive/engineering',
                        help="LCO archive root directory")
    parser.add_argument('--site', dest='site', default=None, help='sites code for camera')
    parser.add_argument('--mintexp', dest='mintexp', default=60, type=float, help='Minimum exposure time to accept')
    parser.add_argument('--redo', action='store_true')
    parser.add_argument('--preview', dest='processstatus', default='processed', action='store_const', const='preview')
    parser.add_argument('--useaws', action='store_true',
                        help="Use LCO archive API to retrieve frame vs direct /archive file mount access")
    mutex = parser.add_mutually_exclusive_group()
    mutex.add_argument('--date', dest='date', default=[None, ], nargs='+', help='Specific date to process.')
    mutex.add_argument('--lastNdays', type=int)

    cameragroup = parser.add_mutually_exclusive_group()
    cameragroup.add_argument('--camera', dest='camera', default=None, help='specific camera to process. ')
    cameragroup.add_argument('--cameratype', dest='cameratype', default=None, choices=['fs', 'fl', 'fa', 'kb'],
                             help='camera type to process at selected sites to process. ')
    cameragroup.add_argument('--crawldirectory', default=None, type=str,
                             help="process all reduced image in specific directoy")

    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper()),
                        format='%(asctime)s.%(msecs).03d %(levelname)7s: %(module)20s: %(message)s')

    args.imagedbPrefix = os.path.expanduser(args.imagedbPrefix)

    if args.outputimageRootDir is not None:
        args.outputimageRootDir = os.path.expanduser(args.outputimageRootDir)
        print("Writing db to directory: %s" % args.outputimageRootDir)

    if args.crawldirectory is not None:
        args.crawldirectory = os.path.expanduser(args.crawldirectory)

    if (args.lastNdays is not None):
        args.date = []
        today = datetime.datetime.utcnow()
        for ii in range(args.lastNdays):
            day = today - datetime.timedelta(days=ii)
            args.date.append(day.strftime("%Y%m%d"))
        args.date = args.date[::-1]

    args.refcat2db = os.path.expanduser(args.refcat2db)
    return args


def photzpmain():
    args = parseCommandLine()

    if args.site is not None:
        sites = [site for site in args.site.split(',')]
    else:
        sites = ('lsc', 'cpt', 'ogg', 'coj', 'tfn', 'elp')

    for date in args.date:
        _logger.info("Processing DAY-OBS {}".format(date))
        if args.cameratype is not None:
            # crawl by camera type
            cameratypes = [x for x in args.cameratype.split(',')]
            for site in sites:
                for cameratype in cameratypes:
                    inputlist = es_aws_imagefinder.get_frames_for_photometry(date, site, cameratype=cameratype,
                                                                             mintexp=args.mintexp)
                    if inputlist is None:
                        _logger.info("None list returned for date {}. Nothing to do here.".format(date))
                        continue
                    imagedb = photdbinterface(args.imagedbPrefix)
                    _logger.info("Processing image list N={} for type {} at site  {} for date {}".format(len(inputlist),
                                                                                                         cameratype,
                                                                                                         site, date))
                    process_imagelist(inputlist, imagedb, args)
                    imagedb.close()

        elif args.camera is not None:
            # crawl for a specific camera
            inputlist = es_aws_imagefinder.get_frames_for_photometry(date, site=None, camera=args.camera,
                                                                     mintexp=args.mintexp)
            if inputlist is None:
                _logger.info("None list returned for date {}. Nothing to do here.".format(date))
                continue
            _logger.info(
                "Processing image list N={} for camera {} at for date {}".format(len(inputlist), args.camera, date))
            imagedb = photdbinterface(args.imagedbPrefix)
            process_imagelist(inputlist, imagedb, args)
            imagedb.close()

        elif args.crawldirectory is not None:
            # Crawl files in a local directory
            print("Not tested")
            inputlist = os.path.basename(glob.glob("{}/*e91.fits.fz".format(args.crawldirectory)))
            imagedb = photdbinterface("%s/%s" % (args.crawldirectory, 'imagezp.db'))
            process_imagelist(inputlist, imagedb, args, rewritetoarchivename=False)
            imagedb.close()

        else:
            print("Need to specify either a camera, or a camera type.")
    sys.exit(0)


if __name__ == '__main__':
    assert sys.version_info >= (3, 5)
    photzpmain()
