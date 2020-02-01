import math
import os
import logging
import numpy as np
from astropy.io import fits

_logger = logging.getLogger(__name__)

class PS1IPP:
    """ Class to access local, distilled copy of PS1 data release.

        Based on code from WIYN ODI quickreduce pipeline, developed by Ralf Kotula. See:
        https://github.com/WIYN-ODI/QuickReduce
    """

    FILTERMAPPING = {}
    FILTERMAPPING['gp'] = {'refMag': 'g', 'colorTerm': 0.0, 'airmassTerm': 0.20, 'defaultZP': 0.0}
    FILTERMAPPING['rp'] = {'refMag': 'r', 'colorTerm': 0.0, 'airmassTerm': 0.12, 'defaultZP': 0.0}
    FILTERMAPPING['ip'] = {'refMag': 'i', 'colorTerm': 0.0, 'airmassTerm': 0.08, 'defaultZP': 0.0}
    FILTERMAPPING['zp'] = {'refMag': 'z', 'colorTerm': 0.0, 'airmassTerm': 0.05, 'defaultZP': 0.0}

    ###  PS to SDSS color transformations according to  Finkbeiner 2016
    ###  http://iopscience.iop.org/article/10.3847/0004-637X/822/2/66/meta#apj522061s2-4 Table 2
    ###  Note that this transformation is valid for stars only. For the purpose of photometric
    ###  calibration, it is desirable to select point sources only from the input catalog.

    ## Why reverse the order of the color term entries? Data are entered in the order as they are
    ## shown in paper. Reverse after the fact to avoid confusion when looking at paper

    ps1colorterms = {}
    ps1colorterms['g'] = [-0.01808, -0.13595, +0.01941, -0.00183][::-1]
    ps1colorterms['r'] = [-0.01836, -0.03577, +0.02612, -0.00558][::-1]
    ps1colorterms['i'] = [+0.01170, -0.00400, +0.00066, -0.00058][::-1]
    ps1colorterms['z'] = [-0.01062, +0.07529, -0.03592, +0.00890][::-1]

    def __init__(self, basedir):
        self.basedir = basedir
        self.skytable = None

    def PS1toSDSS(self, table):
        """
        Modify table in situ from PS1 to SDSS, requires column names compatible with ps1colorterms definition.

        :param table:
        :return: modified table.
        """
        if table is not None:
            pscolor = table['g'] - table['i']
            for filter in self.ps1colorterms:
                colorcorrection = np.polyval(self.ps1colorterms[filter], pscolor)
                table[filter] -= colorcorrection

        return table

    def isInCatalogFootprint(self, ra, dec):
        """ Verify if image is in catalog footprint.
            TODO: Account for image field of view
        """

        # PanSTARRS has valid entries for DEc > - 30 degrees
        return dec >= -30.0

    def get_reference_catalog(self, ra, dec, radius, overwrite_select=False):
        """ Read i fits table from local catalog copy. Concatenate tables columns
           from different fits tables for full coverage.
        """

        # A lot of safeguarding boiler plate to ensure catalog files are valid.
        if (self.basedir is None) or (not os.path.isdir(self.basedir)):
            _logger.error("Unable to find reference catalog: %s" % (str(self.basedir)))
            return None

        # Load the SkyTable so we know in what files to look for the catalog"
        _logger.debug("Using catalog found in %s" % (self.basedir))
        skytable_filename = "%s/SkyTable.fits" % (self.basedir)
        if (not os.path.isfile(skytable_filename)):
            _logger.fatal("Unable to find catalog index file  %s!" % (skytable_filename))
            return None

        # Read in the master index hdu
        skytable_hdu = fits.open(skytable_filename)
        skytable = skytable_hdu['SKY_REGION'].data

        # Select entries that match our list
        # print ra, dec, radius, type(ra), type(dec), type(radius)
        # logger.debug("# Searching for stars within %.1f degress around %f , %f ..." % (radius, ra, dec))

        if (not radius == None and radius > 0):
            min_dec = dec - radius
            max_dec = dec + radius
            min_ra = ra - radius / math.cos(math.radians(dec))
            max_ra = ra + radius / math.cos(math.radians(dec))
        else:
            min_dec, max_dec = dec[0], dec[1]
            min_ra, max_ra = ra[0], ra[1]

        _logger.debug("Querying catalog: Ra=%f...%f Dec=%f...%f" % (min_ra, max_ra, min_dec, max_dec))

        if (max_ra > 360.):
            # This wraps around the high end, shift all ra values by -180
            # Now all search RAs are ok and around the 180, next also move the catalog values
            selected = skytable['R_MIN'] < 180
            skytable['R_MAX'][selected] += 360
            skytable['R_MIN'][selected] += 360
        if (min_ra < 0):
            # Wrap around at the low end
            selected = skytable['R_MAX'] > 180
            skytable['R_MAX'][selected] -= 360
            skytable['R_MIN'][selected] -= 360

        _logger.debug("# Search radius: RA=%.1f ... %.1f   DEC=%.1f ... %.1f" % (min_ra, max_ra, min_dec, max_dec))

        try:
            needed_catalogs = (skytable['PARENT'] > 0) & (skytable['PARENT'] < 25) & \
                              (skytable['R_MAX'] > min_ra) & (skytable['R_MIN'] < max_ra) & \
                              (skytable['D_MAX'] > min_dec) & (skytable['D_MIN'] < max_dec)
        except KeyError:
            # try without the PARENT field
            needed_catalogs = (skytable['R_MAX'] > min_ra) & (skytable['R_MIN'] < max_ra) & \
                              (skytable['D_MAX'] > min_dec) & (skytable['D_MIN'] < max_dec)

        # print skytable[needed_catalogs]

        files_to_read = skytable['NAME'][needed_catalogs]
        files_to_read = [f.strip() for f in files_to_read]
        _logger.debug(files_to_read)

        skytable_hdu.close()  # Warning: might erase the loaded data, might need to copy array!

        # Now quickly go over the list and take care of all filenames that still have a 0x00 in them
        for i in range(len(files_to_read)):
            found_at = files_to_read[i].find('\0')
            if (found_at > 0):
                files_to_read[i] = files_to_read[i][:found_at]

        # Load all frames, one by one, and select all stars in the valid range.
        # Then add them to the catalog with RAs and DECs
        full_catalog = None  # numpy.zeros(shape=(0,6))
        catalog_filenames = []

        # Start iterating though catalogs
        for catalogname in files_to_read:

            catalogfile = "%s/%s" % (self.basedir, catalogname)
            # print catalogfile
            if (not os.path.isfile(catalogfile)):
                # not a file, try adding .fits to the end of the filename
                if (os.path.isfile(catalogfile + ".fits")):
                    catalogfile += ".fits"
                else:
                    # neither option (w/ or w/o .fits added is a file)
                    _logger.warning(
                        "Catalog file (%s) not found (base-dir: %s)" % (os.path.abspath(catalogfile), self.basedir))
                    continue

            try:
                hdu_cat = fits.open(catalogfile)
            except:
                _logger.warning("Unable to open catalog file %s" % (catalogfile))
                continue

            catalog_filenames.append(catalogfile)
            _logger.debug("Adding %s to list of catalog files being used" % (catalogfile))

            # read table into a nd-array buffer
            cat_full = hdu_cat[1].data
            hdu_cat.close()

            # Read the RA and DEC values
            cat_ra = cat_full['RA']
            cat_dec = cat_full['DEC']

            # To select the right region, shift a temporary catalog
            cat_ra_shifted = cat_ra
            if (max_ra > 360.):
                cat_ra_shifted[cat_ra < 180] += 360
            elif (min_ra < 0):
                cat_ra_shifted[cat_ra > 180] -= 360

            select_from_cat = (cat_ra_shifted > min_ra) & (cat_ra_shifted < max_ra) & (cat_dec > min_dec) & (
                cat_dec < max_dec)

            array_to_add = cat_full[select_from_cat]
            _logger.debug("Read %d sources from %s" % (array_to_add.shape[0], catalogname))

            if (full_catalog is None):
                full_catalog = array_to_add
            else:
                full_catalog = np.append(full_catalog, array_to_add, axis=0)
                # print photom_grizy[:3,:]

            if (full_catalog is None):
                _logger.warning("No stars found in area %s, %s from catalog %s" % (
                    str(ra), str(dec),
                    # ra[0], ra[1], dec[0], dec[1],
                    self.basedir))
            else:
                _logger.debug(
                    "Read a total of %d stars from %d catalogs!" % (full_catalog.shape[0], len(files_to_read)))

        self.PS1toSDSS(full_catalog)
        return full_catalog