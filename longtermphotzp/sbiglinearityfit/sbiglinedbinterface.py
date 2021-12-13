import logging
import sys
import datetime
import numpy as np
from astropy.table import Table
import astropy.time as astt
import math
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, create_engine
import os

assert sys.version_info >= (3, 5)
_logger = logging.getLogger(__name__)

Base = declarative_base()


class SBIGLINMeasurement(Base):
    __tablename__ = 'sbiglinearity'

    # def __init__(self, rec):
    #      self.name = rec.name
    #      self.dateobs = rec.dateobs
    #      self.site = rec.site
    #      self.dome = rec.dome
    #      self.telescope = rec.telescope
    #      self.camera = rec.camera
    #      self.filter = rec.filter
    #      if rec.airmass is None:
    #          self.airmass = None
    #      if isinstance(rec.airmass, float):
    #          self.airmass=rec.airmass
    #      else:
    #          self.airmass = None
    #          _logger.warning(f"Air mass is not float: {rec.airmass} {type(rec.airmass)} {float} ")
    #
    #      self.zp = rec.zp if math.isfinite (rec.zp) else math.nan
    #      self.colorterm = rec.colorterm if math.isfinite (rec.colorterm) else math.nan
    #      self.zpsig = rec.zpsig if math.isfinite (rec.zpsig) else math.nan

    name = Column(String, primary_key=True)
    dateobs = Column(String)
    site = Column(String, index=True)
    dome = Column(String, index=True)
    telescope = Column(String, index=True)
    camera = Column(String, index=True)
    filter = Column(String)
    exptime = Column(Float)
    seeing = Column(Float)
    background = Column(Float)
    fit_z = Column(Float)
    fit_k = Column(Float)
    nstars = Column(Integer)

    def __repr__(self):
        return f'{self.name} {self.dateobs} {self.filter} {self.exptime} {self.fit_z: 6.3f} {self.fit_k: 5.3f}'

class sbiglininterface:
    ''' Storage model for data:
    individual photometric zeropoints per exposure
    '''

    # Only one engine per app, but several connections possible
    # Not nicely coded through, better to have a factory method some day.
    engines = {}

    def __init__(self, dburl):
        if dburl not in sbiglininterface.engines:
            _logger.info(f"Creating new database engine for url {dburl}")
            myengine = create_engine(dburl, echo=False)
            sbiglininterface.engines[dburl] = myengine
        else:
            _logger.info(f"Reusing  database engine for url {dburl}")
            myengine = sbiglininterface.engines[dburl]

        SBIGLINMeasurement.__table__.create(bind=myengine, checkfirst=True)
        self.session = sessionmaker(bind=myengine)()

    def addsbiglin(self, sbiglinmeasurementObject, commit=True):

        _logger.debug("addphotzp: %s" % str(sbiglinmeasurementObject))

        existingEntry = self.exists(sbiglinmeasurementObject.name)
        if existingEntry:
            _logger.info(f"Updating exsitng data base entry: {sbiglinmeasurementObject} -> {existingEntry}")
            existingEntry.fit_k = sbiglinmeasurementObject.fit_k
            existingEntry.fit_z = sbiglinmeasurementObject.fit_z

        else:
            _logger.info("Insert: %s" % str(sbiglinmeasurementObject))
            self.session.add(sbiglinmeasurementObject)

        if commit:
            self.session.commit()

    def exists(self, filename):
        """ Check if entry as identified by fil
e name already exists in database
        """

        return self.session.query(SBIGLINMeasurement).filter_by(name=filename).first()

    def close(self):
        """ Close the database safely"""
        _logger.info("Closing data base session")
        self.session.close()

    def readRecords(self, site=None, dome=None, telescope=None, camera=None):
        """  Read the photometry records from the database, optionally filtered by site, dome, telescope, and camera.

        """

        q = self.session.query(SBIGLINMeasurement)
        if site is not None:
            q = q.filter(SBIGLINMeasurement.site == site)
        if dome is not None:
            q = q.filter(SBIGLINMeasurement.dome == dome)
        if telescope is not None:
            q = q.filter(SBIGLINMeasurement.telescope == telescope)
        if camera is not None:
            q = q.filter(SBIGLINMeasurement.camera == camera)

        # TODO: This might consume too much memory.
        allrows = [
            [e.name, e.dateobs, e.site, e.dome, e.telescope, e.camera, e.filter, e.airmass, e.zp, e.colorterm, e.zpsig]
            for e in q.all()]

        if len(allrows) == 0:
            return None
        allrows = np.asarray(allrows)

        t = Table(allrows, names=['name', 'dateobs', 'site', 'dome', 'telescope', 'camera', 'filter', 'airmass', 'zp',
                                  'colorterm', 'zpsig'])
        t['dateobs'] = t['dateobs'].astype(str)
        t['dateobs'] = astt.Time(t['dateobs'], scale='utc', format=None).to_datetime()
        t['zp'] = t['zp'].astype(float)
        t['airmass']['UNKNOWN' == t['airmass']] = 'nan'
        t['airmass'] = t['airmass'].astype(float)
        t['zpsig'] = t['zpsig'].astype(float)
        t['colorterm'] = t['colorterm'].astype(float)


        return t




if __name__ == '__main__':
    # some testing code that should be modified and migrated into the test suite.
    logging.basicConfig(level=getattr(logging, 'DEBUG'),
                        format='%(asctime)s.%(msecs).03d %(levelname)7s: %(module)20s: %(message)s')
    print(os.environ['DATABASE'])

    db = sbiglininterface(os.environ['DATABASE'])
    all = db.readRecords(site='lsc', camera='fa04')
    print("photzp measurement records found: ", len(all))
    mirrormodels = db.findmirrormodels('1m0', 'rp')
    print("Mirror models found", len(mirrormodels), mirrormodels)
    m = db.readmirrormodel(telescopeid='lsc-domb-1m0a', filter='gp')
    db.close()

    db = photdbinterface(os.environ['DATABASE'])
    all = db.readRecords(site='lsc', camera='fa04')
    print("photzp measurement records found: ", len(all))
    mirrormodels = db.findmirrormodels('1m0', 'rp')
    print("Mirror models found", len(mirrormodels), mirrormodels)
    m = db.readmirrormodel(telescopeid='lsc-domb-1m0a', filter='gp')
    db.close()
