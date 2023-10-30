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


class PhotZPMeasurement(Base):
    __tablename__ = 'lcophot'

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
    airmass = Column(Float)
    zp = Column(Float)
    colorterm = Column(Float)
    zpsig = Column(Float)

    def __repr__(self):
        return f'{self.name} {self.dateobs} {self.filter} {self.zp}'


class TelescopeThroughputModelPoint(Base):
    __tablename__ = 'telescopemodel_ver2'
    entryid = Column(Integer, primary_key=True)
    telescopeid = Column(String)
    filter = Column(String)
    dateobs = Column(String)
    modelzp = Column(Float)


class photdbinterface:
    ''' Storage model for data:
    individual photometric zeropoints per exposure
    long term mirror model: upper envelope fit for a telescope's trendline
    '''

    # Only one engine per app, but several connections possible
    # Not nicely coded through, better to have a factory method some day.
    engines = {}

    def __init__(self, dburl):
        if dburl not in photdbinterface.engines:
            _logger.info(f"Creating new database engine for url {dburl}")
            myengine = create_engine(dburl, echo=False)
            photdbinterface.engines[dburl] = myengine
        else:
            _logger.info(f"Reusing  database engine for url {dburl}")
            myengine = photdbinterface.engines[dburl]

        PhotZPMeasurement.__table__.create(bind=myengine, checkfirst=True)
        TelescopeThroughputModelPoint.__table__.create(bind=myengine, checkfirst=True)
        self.session = sessionmaker(bind=myengine)()

    def addphotzp(self, photmeasurementObject, commit=True):

        _logger.debug("addphotzp: %s" % str(photmeasurementObject))

        existingEntry = self.exists(photmeasurementObject.name)
        if existingEntry:
            _logger.info(f"Updating exsitng data base entry: {photmeasurementObject} -> {existingEntry}")
            existingEntry.zp = photmeasurementObject.zp
            existingEntry.zpsig = photmeasurementObject.zpsig
            existingEntry.colorterm = photmeasurementObject.colorterm
        else:
            _logger.info("Insert: %s" % str(photmeasurementObject))
            self.session.add(photmeasurementObject)

        if commit:
            self.session.commit()

    def exists(self, filename):
        """ Check if entry as identified by file name already exists in database
        """
        return self.session.query(PhotZPMeasurement).filter_by(name=filename).first()

    def close(self):
        """ Close the database safely"""
        _logger.info("Closing data base session")
        self.session.close()

    def readRecords(self, site=None, dome=None, telescope=None, camera=None, filter = None):
        """  Read the photometry records from the database, optionally filtered by site, dome, telescope, and camera.

        """

        q = self.session.query(PhotZPMeasurement)
        if site is not None:
            q = q.filter(PhotZPMeasurement.site == site)
        if dome is not None:
            q = q.filter(PhotZPMeasurement.dome == dome)
        if telescope is not None:
            q = q.filter(PhotZPMeasurement.telescope == telescope)
        if camera is not None:
            q = q.filter(PhotZPMeasurement.camera == camera)
        if filter is not None:
            q = q.filter(PhotZPMeasurement.filter.in_(filter))

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


        _logger.info (f"Filter set:  {set (t['filter'])}")
        _logger.info (f"Camera set:  {set (t['camera'])}")

        if 'fl06' in t['camera']:
            # fl06 was misconfigured with a wrong gain, which trickles down through the banzai processing.
            # The correct gain was validated Nov 27th 2017 on existing data.
            dateselect = (t['dateobs'] < datetime.datetime(year=2017, month=11, day=17)) & (t['camera'] == 'fl06')
            t['zp'][dateselect] = t['zp'][dateselect] - 2.5 * math.log10(1.82 / 2.45)

        if 'fl05' in t['camera']:
            # fl06 was misconfigured with a wrong gain, which trickles down through the banzai processing.
            # The correct gain was validated Nov 27th 2017 on existing data.
            dateselect = (t['camera'] == 'fl05')
            t['zp'][dateselect] = t['zp'][dateselect] - 2.5 * math.log10(1.69 / 2.09)

        if 'fl11' in t['camera']:
            #
            dateselect = (t['camera'] == 'fl11')
            t['zp'][dateselect] = t['zp'][dateselect] - 2.5 * math.log10(1.85 / 2.16)

        if 'kb96' in t['camera']:
            dateselect = (t['dateobs'] > datetime.datetime(year=2017, month=11, day=15)) & (
                    t['dateobs'] < datetime.datetime(year=2018, month=4, day=10)) & (t['camera'] == 'kb96')
            t['zp'][dateselect] = t['zp'][dateselect] - 2.5 * math.log10(0.851 / 2.74)

        if 'kb95' in t['camera']:
            dateselect = (t['dateobs'] > datetime.datetime(year=2018, month=9, day=18)) & (t['camera'] == 'kb95')
            t['zp'][dateselect] = t['zp'][dateselect] - 2.5 * math.log10(2.75 / 1.6)

        if 'fs02' in t['camera']:
            # https://github.com/LCOGT/site-configuration/commit/26d03f28868579d49dcc5e5e4e6a6650651ae72c
            dateselect = (t['dateobs'] < datetime.datetime(year=2019, month=3, day=12)) & (t['camera'] == 'fs02')
            t['zp'][dateselect] = t['zp'][dateselect] - 2.5 * math.log10(8.09 / 7.7)

        if 'fs01' in t['camera']:
            # https://github.com/LCOGT/site-configuration/commit/26d03f28868579d49dcc5e5e4e6a6650651ae72c
            dateselect = (t['dateobs'] < datetime.datetime(year=2019, month=3, day=12)) & (t['camera'] == 'fs01')
            t['zp'][dateselect] = t['zp'][dateselect] - 2.5 * math.log10(8.14 / 7.7)

        return t

    def readmirrormodel(self, telescopeid, filter):
        """ read a mirrormodel by telesope identifer and filter .
         Returns:
             (date-obs, modelzp) : tupel of two arrays containg model date, and model photoemtric zeropoint.
         """
        t = None
        _logger.debug("reading data for mirror model [%s] [%s]" % (telescopeid, filter))
        q = self.session.query(TelescopeThroughputModelPoint)
        if telescopeid is not None:
            q = q.filter(TelescopeThroughputModelPoint.telescopeid == telescopeid)
        if filter is not None:
            q = q.filter(TelescopeThroughputModelPoint.filter == filter)
        allrows = np.asarray([[e.dateobs, e.modelzp] for e in q.all()])
        t = Table(allrows, names=['dateobs', 'zp'])
        if len(t) > 0:
            t['dateobs'] = t['dateobs'].astype(str)
            t['dateobs'] = astt.Time(t['dateobs'], scale='utc', format=None).to_datetime()
            t['zp'] = t['zp'].astype(float)
        else:
            return None
        return t

    def storemirrormodel(self, telescopeid, filter, dates, zps, commit=True):

        _logger.info("Store mirror model for: [%s] filter [%s], %d records" % (telescopeid, filter, len(dates)))

        # self.session("delete from telescopemodel where telescopeid like ? AND filter like ?",
        #              (telescopeid, filter))

        self.session.query(TelescopeThroughputModelPoint).filter(
            TelescopeThroughputModelPoint.telescopeid == telescopeid).filter(
            TelescopeThroughputModelPoint.filter == filter).delete()

        for ii in range(len(dates)):
            mp = TelescopeThroughputModelPoint(telescopeid=telescopeid, dateobs=dates[ii], modelzp=zps[ii],
                                               filter=filter)
            self.session.add(mp)
            # self.conn.execute("insert or replace into telescopemodel values (?,?,?,?)",
            #                   (telescopeid, filter, dates[ii], zps[ii]))

        if (commit):
            self.session.commit()

        pass

    def findmirrormodels(self, telescopeclass, filter):
        _logger.debug("Searching for mirror models with contraint %s %s" % (telescopeclass, filter))

        q = self.session.query(TelescopeThroughputModelPoint.telescopeid).filter(
            TelescopeThroughputModelPoint.filter == filter).filter(
            TelescopeThroughputModelPoint.telescopeid.like(f'%{telescopeclass}%')).distinct()
        rows = q.all()
        allrows = np.asarray([e.telescopeid for e in rows])
        _logger.info("Uniqe identifiers: %s" % allrows)
        return allrows


if __name__ == '__main__':
    # some testing code that should be modified and migrated into the test suite.
    logging.basicConfig(level=getattr(logging, 'DEBUG'),
                        format='%(asctime)s.%(msecs).03d %(levelname)7s: %(module)20s: %(message)s')
    print(os.environ['DATABASE'])

    db = photdbinterface(os.environ['DATABASE'])
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
