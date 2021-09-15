import astropy
import matplotlib
from scipy import optimize

import longtermphotzp.es_aws_imagefinder as es_aws_imagefinder
from longtermphotzp.atlasrefcat2 import atlas_refcat2
from longtermphotzp.photdbinterface import photdbinterface, PhotZPMeasurement

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

    def __init__(self, refcat2_url):
        self.referencecatalog = atlas_refcat2(refcat2_url)

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
        retCatalog['WCSERR'] =  imageobject['SCI'].header['WCSERR']

        # Check if WCS is OK, otherwise we could not cross-match with catalog
        if retCatalog['WCSERR'] != 0:
            _logger.info(
                f"WCS solve not valid in FITS header. Skipping. Error code is: {retCatalog['WCSERR']}")
            return None

        # Check if filter is supported
        if retCatalog['instfilter'] not in self.referencecatalog.FILTERMAPPING:
            _logger.info(
                "Filter %s not viable for photometric calibration. Sorry" % (retCatalog['instfilter']))
            return None

        # Check if exposure time is long enough
        if (retCatalog['exptime'] < mintexp):
            _logger.info("Exposure %s time is deemed too short, ignoring" % (retCatalog['exptime']))
            return None

        # verify there is no deliberate defocus
        if (retCatalog['FOCOBOFF'] is not None) and (retCatalog['FOCOBOFF'] != 0):
            _logger.info("Exposure is deliberately defocussed by %s, ignoring" % (retCatalog['FOCOBOFF']))
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
            _logger.error("Failed to convert images coordinates to world coordinates. Giving up on file.")
            return None

        # Query reference catalog TODO: paramterize FoV of query!
        refcatalog = self.referencecatalog.get_reference_catalog(ra, dec, 0.33)
        if refcatalog is None:
            _logger.warning("no reference catalog received.")
            return None

        # Start the catalog matching, using astropy skycoords built-in functions.
        cInstrument = SkyCoord(ra=ras * u.degree, dec=decs * u.degree)
        cReference = SkyCoord(ra=refcatalog['ra'] * u.degree, dec=refcatalog['dec'] * u.degree)
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

        instmagzero = -2.5 * np.log10(instCatalog['FLUX'][condition])

        # Calculate the magnitude difference between reference and inst catalog
        retCatalog['instmag'] = instmag
        retCatalog['instmagzero'] = instmagzero
        retCatalog['refcol'] = (refcatalog['gmag'] - refcatalog['imag'])[condition]
        retCatalog['refcolerr'] = np.sqrt(refcatalog['gmagerr']**2 + refcatalog['imagerr']**2)[condition]
        retCatalog['refmag'] = refcatalog[referenceFilterName][condition]
        retCatalog['refmagerr'] =  refcatalog[f'{referenceFilterName}err'][condition]
        retCatalog['ra'] = refcatalog['ra'][condition]
        retCatalog['dec'] = refcatalog['dec'][condition]
        retCatalog['matchDistance'] = distance[condition]
        retCatalog['x'] = instCatalog['x'][condition]
        retCatalog['y'] = instCatalog['y'][condition]

        return retCatalog

    def reject_outliers(self, data, m=2):
        """
        Reject data from vector that are > m std deviations from median
        :param m:
        :return:
        """
        std = np.std(data)
        return data[abs(data - np.median(data)) < m * std]


    def robustfit (self, deltamag, refcol):
        #Initial preselection based on absoute values
        cond = (refcol > 0) & (refcol < 3) & (np.abs( (deltamag - np.median (deltamag))) < 0.75)
        colorparams = np.polyfit(refcol[cond], deltamag[cond], 1)
        color_p = np.poly1d(colorparams)
        delta = np.abs(deltamag - color_p(refcol))
        cond = (delta < 0.2) & (delta < 2 * np.std (delta))
        colorparams = np.polyfit(refcol[cond], deltamag[cond], 1)
        color_p = np.poly1d(colorparams)
        new_colorterm = colorparams[0]
        new_zeropoint = colorparams[1]
        new_std = np.std (  (deltamag - color_p(refcol))[cond] )
        _logger.debug (f'Fit: zp = {new_zeropoint} color = {new_colorterm} rms = {new_std}')
        return colorparams, cond


    def analyzeImage(self, imageentry, outputdb=None,
                     outputimageRootDir=None, mintexp=60, useaws=False):
        """
            Do full photometric zeropoint analysis on an image. This is the main entry point

            param iamgeentry: Table row to caontain 'filename' and 'frameid'
        """

        # The filename may or may not be the full path to the image
        filename = str(imageentry['filename'])
        frameid = int(imageentry['frameid'])
        imageName = os.path.basename(filename)
        _logger.info(f'\n\nImage {filename} {frameid} iamgeName for DB is {imageName}\n\n')

        # Read banzai star catalog
        try:
            if useaws:
                _logger.debug("Use AWS")
                imageobject = es_aws_imagefinder.download_from_archive(frameid)
            else:
                _logger.info("Loading from file system: {}".format(filename))
                imageobject = fits.open(filename)
        except:
            _logger.warning("File {} could not be accessed: {}".format(filename, sys.exc_info()[0]))
            return 0, 0, 0

        retCatalog = self.generateCrossmatchedCatalog(imageobject, mintexp=mintexp)
        imageobject.close()
        if (retCatalog is None) or (retCatalog['instmag'] is None) or (len(retCatalog['ra']) < 10):
            if retCatalog is None:
                _logger.info(f"No matched catalog was returned for image {imageName}")
                return

            if len(retCatalog['ra']) < 10:
                _logger.info("%s: Catalog returned, but is has less than 10 stars. Ignoring. " % (imageentry))
            return

        # calculate the per star zeropoint
        magZP = retCatalog['refmag'] - retCatalog['instmag']
        refmag = retCatalog['refmag']
        refcol = retCatalog['refcol']

        # First guess
        cleandata = self.reject_outliers(magZP, 3)
        firstguess_photzp = np.median(cleandata)
        photzpsig = np.std(cleandata)

        # calculate color term
        try:
            #old way:
            # cond = (refcol > 0) & (refcol < 3) & (np.abs(magZP - photzp) < 0.75)
            # colorparams = np.polyfit(refcol[cond], (magZP - photzp)[cond], 1)
            # color_p = np.poly1d(colorparams)
            # delta = np.abs(magZP - photzp - color_p(refcol))
            # cond = (delta < 0.2)
            # colorparams = np.polyfit(refcol[cond], (magZP - photzp)[cond], 1)
            # color_p = np.poly1d(colorparams)
            # colorterm = colorparams[0]

            # the new way
            newcolorparam, new_cond = self.robustfit(magZP,refcol)
            colorterm = newcolorparam[0]
            photzp = newcolorparam[1]
            color_p = np.poly1d(newcolorparam)
            print (f"New zeropoint, color term: {photzp}, {colorterm}")

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
            plt.plot(refmag[~new_cond], (magZP - color_p(refcol) + photzp)[~new_cond], 'x', color='grey')
            plt.plot(refmag[new_cond], (magZP - color_p(refcol)+photzp)[new_cond], '.', color='red')
            plt.xlim([10, 22])
            plt.ylim([photzp - 0.5, photzp + 0.5])
            plt.axhline(y=photzp, color='r', linestyle='-')
            plt.xlabel("Reference catalog mag")
            plt.ylabel("Reference Mag - Instrumental Mag (%s)" % (retCatalog['instfilter']))
            plt.title("Photometric zeropoint %s %5.2f" % (outbasename, photzp))
            plt.savefig("%s/%s_%s_zp.png" % (outputimageRootDir, outbasename, retCatalog['instfilter']))
            plt.close()

            ### Zeropoint plot, but based on instrumental magnitudes.
            # plt.figure()
            # plt.plot(retCatalog['instmagzero'][~new_cond], (magZP - color_p(refcol) + photzp)[~new_cond], 'x', color='grey')
            # plt.plot(retCatalog['instmagzero'][new_cond], (magZP - color_p(refcol)+photzp)[new_cond], '.', color='red')
            # plt.xlim([-20, -7.5])
            # plt.ylim([photzp - 0.5, photzp + 0.5])
            # plt.axhline(y=photzp, color='r', linestyle='-')
            # plt.xlabel("Instrumental Magnitude, not exp time corrected")
            # plt.ylabel("Reference Mag - Instrumental Mag (%s)" % (retCatalog['instfilter']))
            # plt.title("Photometric zeropoint %s %5.2f" % (outbasename, photzp))
            # plt.savefig("%s/%s_%s_zp_inst.png" % (outputimageRootDir, outbasename, retCatalog['instfilter']))
            # plt.close()




            ### Color term plot
            plt.figure()
            plt.plot(refcol[~new_cond], magZP[~new_cond] , 'x',  color='grey')
            plt.plot(refcol[new_cond], magZP[new_cond] , '.',  color='red')
            plt.axhline(y=photzp, color='grey', linestyle='-', label=f"zeropoint {photzp:5.2f}")

            if color_p is not None:
                xp = np.linspace(-0.5, 3.5, 10)
                plt.plot(xp, color_p(xp), '--', color='blue', label=f"color term {colorterm:5.3f}" )
                plt.legend()

            plt.xlim([-0.5, 3.0])
            plt.ylim([photzp - 0.5, photzp + 0.5])
            plt.xlabel("(g-i)$_{\\rm{SDSS}}$ Reference")
            plt.ylabel("Reference Mag - Instrumental Mag  %s" % ( retCatalog['instfilter']))
            plt.title("Color correction %s " % (outbasename))
            plt.savefig("%s/%s_%s_color.png" % (outputimageRootDir, outbasename, retCatalog['instfilter']))
            plt.close()

            ### x/y/r variations in photometric zeropoint

            plt.figure ()

            residual = magZP[new_cond] - color_p (refcol[new_cond])
            plt.subplot (3,1,1)
            plt.plot (retCatalog['x'][new_cond], residual,'.')
            plt.ylim([-0.2,0.2])
            plt.ylabel ("\nCCD X")

            plt.title("Residuals of zero point %s " % (outbasename))

            plt.subplot (3,1,2)
            plt.plot (retCatalog['y'][new_cond], residual,'.')
            plt.ylim([-0.2,0.2])
            plt.xlabel ("y coordinate [pixel]")
            plt.ylabel (f'residual in {retCatalog["instfilter"]}[mag]\nCCD-Y')

            plt.subplot (3,1,3)
            plt.plot (np.sqrt (  (retCatalog['x'][new_cond]-1024) **2 + (retCatalog['x'][new_cond]-1024) **2), residual,'.')
            plt.ylim([-0.2,0.2])
            plt.xlabel ("coordinate [pixel]")
            plt.ylabel (f'\nradial')


            plt.savefig("%s/%s_%s_residuals.png" % (outputimageRootDir, outbasename, retCatalog['instfilter']), bbox_inches='tight')
            plt.close()

        if outputdb is not None:
            m = PhotZPMeasurement(name=imageName, dateobs=retCatalog['dateobs'].replace('T', ' '),
                                  site=retCatalog['siteid'], dome=retCatalog['domid'],
                                  telescope=retCatalog['telescope'], camera=retCatalog['instrument'],
                                  filter=retCatalog['instfilter'], airmass=retCatalog['airmass'],
                                  zp=photzp, colorterm=colorterm, zpsig=photzpsig)
            outputdb.addphotzp(m)
        else:
            _logger.warning("Not saving output for image %s " % imageName)

        return photzp, photzpsig, colorterm


def process_imagelist(inputlist: astropy.table.Table, db, args, rewritetoarchivename=True, inputlistIsArchiveID=False):
    """ Invoke the per image processing for a list of files, but check for duplication. """
    # get list of files of interest from elasticsearch
    initialsize = len(inputlist)
    rejects = []
    if not args.redo:
        for image in inputlist['filename']:
            if db.exists(image):
                rejects.append(image)

        for r in rejects:
            pass
            # TODO: find out how to delete table entries that are duplicate
            row = np.where(inputlist['filename'] == r)
            if len(row) > 0:
                row = row[0][0]
                _logger.debug(f"remove duplicate from table: {r} at row {row}")
                inputlist.remove_row(row)

            # inputlist.remove(r)
    _logger.info("Found %d files initially, but cleaned %d already measured images. Starting analysis of %d files" % (
        initialsize, len(rejects), len(inputlist)))

    photzpStage = PhotCalib(args.refcat2_url)
    for image in inputlist:
        if rewritetoarchivename:
            fn = lcofilename_to_archivepath(image['filename'], args.rootdir)
            image = Table(np.asarray([fn, image['frameid']]), names=['filename', 'frameid'])
        _logger.info("processimagelist: send of to analyze image: \n{}".format(image))
        photzpStage.analyzeImage(image, outputdb=db, outputimageRootDir=args.outputimageRootDir, mintexp=args.mintexp,
                                 useaws=args.useaws)


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
    parser.add_argument('--refcat2-url', dest='refcat2_url', default='http://phot-catalog.lco.gtn/',
                        help='URL of Atlas refcat2 catalog database')
    parser.add_argument("--diagnosticplotsdir", dest='outputimageRootDir', default=None,
                        help='Output directory for diagnostic photometry plots. No plots generated if option is omitted. This is a time consuming task. ')
    parser.add_argument('--photodb', dest='imagedbPrefix', default=f'sqlite:///{os.path.expanduser("~/lcophotzp.db")}',
                        help='Result output directory. .db file is written here')
    parser.add_argument('--imagerootdir', dest='rootdir', default='/archive/engineering',
                        help="LCO archive root directory")
    parser.add_argument('--site', dest='site', default=None, help='sites code for camera')
    parser.add_argument('--mintexp', dest='mintexp', default=10, type=float, help='Minimum exposure time to accept')
    parser.add_argument('--redo', action='store_true')
    parser.add_argument('--preview', dest='processstatus', default='processed', action='store_const', const='preview')
    parser.add_argument('--useaws', action='store_true',
                        help="Use LCO archive API to retrieve frame vs direct /archive file mount access")
    mutex = parser.add_mutually_exclusive_group()
    mutex.add_argument('--date', dest='date', default=[], nargs='+', help='Specific date to process.')
    mutex.add_argument('--lastNdays', type=int)

    cameragroup = parser.add_mutually_exclusive_group()
    cameragroup.add_argument('--camera', dest='camera', default=None, help='specific camera to process. ')
    cameragroup.add_argument('--cameratype', dest='cameratype', default=None, choices=['fs', 'fl', 'fa', 'kb', 'ep'],
                             help='camera type to process at selected sites to process. ')
    cameragroup.add_argument('--crawldirectory', default=None, type=str,
                             help="process all reduced image in specific directoy")

    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper()),
                        format='%(asctime)s.%(msecs).03d %(levelname)7s: %(module)20s: %(message)s')

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
    return args


def photzpmain():
    args = parseCommandLine()

    if args.site is not None:
        sites = [site for site in args.site.split(',')]
    else:
        sites = ('lsc', 'cpt', 'ogg', 'coj', 'tfn', 'elp')

    print('DATES: ', args.date)
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



        else:
            print("Need to specify either a camera, or a camera type.")
    if args.crawldirectory is not None:
        # Crawl files in a local directory
        print(f"Not tested {args.crawldirectory}")
        inputlist = (glob.glob(f"{args.crawldirectory}/*[es]91.fits.fz"))
        inputlist = Table([inputlist, [-1] * len(inputlist)], names=['filename', 'frameid'])
        imagedb = photdbinterface("sqlite:///%s/%s" % (args.crawldirectory, 'imagezp.db'))
        process_imagelist(inputlist, imagedb, args, rewritetoarchivename=False)
        imagedb.close()

    sys.exit(0)


if __name__ == '__main__':
    assert sys.version_info >= (3, 5)
    photzpmain()
