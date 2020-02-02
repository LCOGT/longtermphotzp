import logging
import sys
import sqlite3
import datetime
import numpy as np
from astropy.table import Table
import astropy.time as astt
import math

from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database

assert sys.version_info >= (3, 5)
_logger = logging.getLogger(__name__)

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, create_engine

Base = declarative_base()


class PhotZPMeasurement(Base):
    __tablename__ = 'lcophot'
    name = Column(String, primary_key=True)
    dateobs = Column(String)
    site = Column(String)
    dome = Column(String)
    telescope = Column(String)
    camera = Column(String)
    filter = Column(String)
    airmass = Column(Float)
    zp = Column(Float)
    colorterm = Column(Float)
    zpsig = Column(Float)


class TelecopeThroughputModelPoint(Base):
    __tablename__ = 'telescopemodel'
    telescopeid = Column(String, primary_key=True)
    filter = Column(String)
    dateobs = Column(String)
    modelzp = Column(Float)


class photdbinterface:
    ''' Storage model for data:
    individual photometric zeropoints per exposure
    long term mirror model: upper envelope fit for a telescope's trendline
    '''

    createstatement = "CREATE TABLE IF NOT EXISTS lcophot (" \
                      "name TEXT PRIMARY KEY, " \
                      "dateobs text," \
                      " site text," \
                      " dome text," \
                      " telescope text," \
                      " camera text," \
                      " filter text," \
                      " airmass real," \
                      " zp real," \
                      " colorterm real," \
                      " zpsig real)"

    createmodeldb = "CREATE TABLE IF NOT EXISTS telescopemodel (" \
                    "telescopeid TEXT, " \
                    " filter text," \
                    " dateobs text," \
                    " modelzp real" \
                    " )"

    def __init__(self, fname):
        _logger.debug("Open data base file %s" % (fname))
        self.engine = create_engine(f'sqlite:///{fname}', echo=True)
        if not database_exists(self.engine.url):
            create_database(self.engine.url)
        PhotZPMeasurement.__table__.create(bind=self.engine, checkfirst=True)
        TelecopeThroughputModelPoint.__table__.create(bind=self.engine, checkfirst=True)
        self.session = sessionmaker(bind=self.engine)()

    def addphotzp(self, photmeasurementObject, commit=True):
        _logger.info("About to insert: %s" % str(photmeasurementObject))
        existingEntry = self.exists(photmeasurementObject.name)
        if existingEntry:
            print("Allready in db: {}".format(existingEntry))
            existingEntry.zp = 3
        else:
            self.session.add(photmeasurementObject)
        if commit:
            self.session.commit()

    def exists(self, filename):
        """ Check if entry as identified by file name already exists in database
        """
        return self.session.query(PhotZPMeasurement).filter_by(name=filename).first()

    def close(self):
        """ Close the database safely"""
        _logger.debug("Closing data base session")
        self.session.close()

    def readRecords(self, site=None, dome=None, telescope=None, camera=None):
        """  Read the photometry records fromt eh database, optionally filtered by site, dome, telescope, and camera.

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
        q = self.session.query(TelecopeThroughputModelPoint)
        if telescopeid is not None:
            q = q.filter(TelecopeThroughputModelPoint.telescopeid == telescopeid)
        if filter is not None:
            q = q.filter(TelecopeThroughputModelPoint.filter == filter)

        allrows = np.asarray([[e.dateobs, e.modelzp] for e in q.all()])
        print("All rows: ", allrows)
        t = Table(allrows, names=['dateobs', 'zp'])
        if len(t) > 0:
            t['dateobs'] = t['dateobs'].astype(str)
            t['dateobs'] = astt.Time(t['dateobs'], scale='utc', format=None).to_datetime()
            t['zp'] = t['zp'].astype(float)
        else:
            return None
        return t

    def storemirrormodel(self, telescopeid, filter, dates, zps, commit=True):

        _logger.debug("Store mirror model for: [%s] filter [%s], %d records" % (telescopeid, filter, len(dates)))

        with self.conn:
            self.conn.execute("delete from telescopemodel where telescopeid like ? AND filter like ?",
                              (telescopeid, filter))
            for ii in range(len(dates)):
                # TODO: nuke the old model

                self.conn.execute("insert or replace into telescopemodel values (?,?,?,?)",
                                  (telescopeid, filter, dates[ii], zps[ii]))

        if (commit):
            self.conn.commit()

        pass

    def findmirrormodels(self, telescopeclass, filter):
        _logger.debug("Searching for mirror models with contraint %s %s" % (telescopeclass, filter))

        q = self.session.query(TelecopeThroughputModelPoint).filter(
            TelecopeThroughputModelPoint.filter == filter).filter(
            TelecopeThroughputModelPoint.telescopeid.like(f'%{telescopeclass}%')).distinct(
            TelecopeThroughputModelPoint.telescopeid)
        rows = q.all()
        allrows = np.asarray([e.telescopeid for e in rows])
        _logger.debug("Uniqe identifiers: %s" % allrows)
        return allrows


if __name__ == '__main__':
    print("Hello")
    db = photdbinterface("lcophotzp.db")

    # all = db.readRecords(site='lsc', camera='fa04')
    # print(len(all))
    # print(db.findmirrormodels('1m0', 'rp'))
    m = db.readmirrormodel(telescopeid='lsc-domb-1m0a', filter='zp')
    print(m)
    db.close()
