import logging
import sys
import sqlite3
import datetime
import numpy as np
from astropy.table import Table
import astropy.time as astt
import math




assert sys.version_info >= (3,5)
_logger = logging.getLogger(__name__)


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


    createmodeldb  = "CREATE TABLE IF NOT EXISTS telescopemodel (" \
                      "telescopeid TEXT, " \
                      " filter text," \
                      " dateobs text," \
                      " modelzp real" \
                      " )"



    def __init__(self, fname):
        _logger.debug ("Open data base file %s" % (fname))
        self.sqlite_file = fname
        self.conn = sqlite3.connect(self.sqlite_file)
        self.conn.execute(self.createstatement)
        self.conn.execute(self.createmodeldb)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.commit()

    def addphotzp (self, datablob, commit = True) :

        _logger.info ("About to insert: %s" % str(datablob))

        with self.conn:
            self.conn.execute ("insert or replace into lcophot values (?,?,?,?,?,?,?,?,?,?,?)", datablob)

            if (commit):
                self.conn.commit()


    def exists(self, fname):
        """ Check if entry as identified by file name already exists in database
        """

        cursor = self.conn.execute ("select * from lcophot where name=? limit 1", (fname,))
        res = cursor.fetchone()
        if res is None:
            return False
        return (len (res) > 0)





    # def readoldfile (self, oldname):
    #     """ Ingest a legacy ascii photomerty zeropoint file."""
    #     _logger.error ("DEPRECATED, existing procedure with no action")



    def close(self):
        """ Clode the database safely"""

        _logger.debug ("Closing data base file %s " % (self.sqlite_file))
        self.conn.commit()
        self.conn.close()


    def readRecords (self, site = None, dome = None, telescope = None, camera = None):
        """  Read the photometry records fromt eh database, optionally filtered by site, dome, telescope, and camera.

        """


        query = "select name,dateobs,site,dome,telescope,camera,filter,airmass,zp,colorterm,zpsig from lcophot " \
                "where (site like ? AND dome like ? AND telescope like ? AND camera like ?)"

        args = (site if site is not None else '%',
                dome if dome is not None else '%',
                telescope if telescope is not None else '%',
                camera if camera is not None else '%',)

        cursor = self.conn.execute(query, args)

        allrows = np.asarray(cursor.fetchall())
        if len (allrows) == 0:
            return None

        t = Table (allrows, names = ['name','dateobs','site','dome','telescope','camera','filter','airmass','zp','colorterm','zpsig'])
        t['dateobs'] = t['dateobs'].astype (str)
        t['dateobs'] = astt.Time(t['dateobs'], scale='utc', format=None).to_datetime()

        t['zp'] = t['zp'].astype(float)

        t['airmass'] [ 'UNKNOWN' == t['airmass'] ]  = 'nan'
        t['airmass'] = t['airmass'].astype(float)

        t['zpsig'] = t['zpsig'].astype(float)
        t['colorterm'] = t['colorterm'].astype(float)


        if 'fl06' in t['camera']:
            # fl06 was misconfigured with a wrong gain, which trickles down through the banzai processing.
            # The correct gain was validated Nov 27th 2017 on existing data.
            dateselect = ( t['dateobs'] < datetime.datetime(year=2017,month=11,day=17) ) & (t['camera'] == 'fl06')
            t['zp'][dateselect] = t['zp'][dateselect] - 2.5 * math.log10 (1.82 / 2.45)

        if 'fl05' in t['camera']:
            # fl06 was misconfigured with a wrong gain, which trickles down through the banzai processing.
            # The correct gain was validated Nov 27th 2017 on existing data.
            dateselect =  (t['camera'] == 'fl05')
            t['zp'][dateselect] = t['zp'][dateselect] - 2.5 * math.log10 (1.69 / 2.09)

        if 'fl11' in  t['camera']:
            #
            dateselect =  (t['camera'] == 'fl11')
            t['zp'][dateselect] = t['zp'][dateselect] - 2.5 * math.log10 (1.85 / 2.16)

        if 'kb96' in t['camera']:
            dateselect = ( t['dateobs'] > datetime.datetime(year=2017,month=11,day=15) ) & ( t['dateobs'] < datetime.datetime(year=2018,month=4,day=10) ) & (t['camera'] == 'kb96')
            t['zp'][dateselect] = t['zp'][dateselect] - 2.5 * math.log10 (0.851 / 2.74)

        # align kb past of elp for SPIE 2018 presentation
        #if 'kb74' in t['camera']:
        #    dateselect =  (t['camera'] == 'kb74') & (t['site'] == 'elp')
        #    t['zp'][dateselect] = t['zp'][dateselect] +0.75

        return t


    def readmirrormodel(self, telescopeid, filter):
        """ read a mirrormodel by telesope identifer and filter .
         Returns:
             (date-obs, modelzp) : tupel of two arrays containg model date, and model photoemtric zeropoint.
         """
        t = None
        _logger.debug ("reading data for mirror model [%s] [%s]" % (telescopeid, filter))
        with self.conn:
            cursor = self.conn.execute("select dateobs,modelzp from telescopemodel where (telescopeid like ?) and (filter like ?)",
                              (telescopeid,filter))
            allrows = np.asarray(cursor.fetchall())
            t = Table (allrows, names = ['dateobs','zp'])
            t['dateobs'] = t['dateobs'].astype (str)
            t['dateobs'] = astt.Time(t['dateobs'], scale='utc', format=None).to_datetime()
            t['zp'] = t['zp'].astype(float)
        return t

    def storemirrormodel(self, telescopeid, filter, dates, zps, commit=True):

        _logger.debug ("Store mirror model for: [%s] filter [%s], %d records" % (telescopeid,filter,len(dates)))

        with self.conn:
            self.conn.execute("delete from telescopemodel where telescopeid like ? AND filter like ?", (telescopeid,filter))
            for ii in range (len(dates)):
                # TODO: nuke the old model

                self.conn.execute ("insert or replace into telescopemodel values (?,?,?,?)", (telescopeid,filter,dates[ii],zps[ii]))

        if (commit):
            self.conn.commit()

        pass



    def findmirrormodels (self, telescopeclass, filter):
        _logger.debug ("Searching for mirror models with contraint %s %s" % (telescopeclass,filter))

        with self.conn:
            cursor = self.conn.execute ("select DISTINCT telescopeid from telescopemodel where (filter like ?) and (telescopeid like ?)",
                                         (filter,  "%%%s%%" % telescopeclass))
            allrows = np.asarray(cursor.fetchall()).flatten().astype(str)

            _logger.debug ("Uniqe identifiers: %s" % allrows)

        return allrows