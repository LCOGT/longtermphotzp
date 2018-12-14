import sqlite3
from sqlalchemy import Column, Integer, Float, create_engine, pool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
import gzip
import glob

log = logging.getLogger(__name__)
logging.basicConfig(level='INFO',
                    format='%(asctime)s.%(msecs).03d %(levelname)7s: %(module)20s: %(message)s')
Base = declarative_base()


class Star(Base):
    __tablename__ = 'sources'
    objid = Column(Integer, primary_key=True)
    RA = Column(Float)
    Dec = Column(Float)
    plx = Column(Float)
    pmra = Column(Float)
    pmdec = Column(Float)

    g = Column(Float)
    r = Column(Float)
    i = Column(Float)
    z = Column(Float)

    dg = Column(Float)
    dr = Column(Float)
    di = Column(Float)
    dz = Column(Float)


class Position(Base):
    __tablename__ = 'positions'
    objid = Column(Integer, primary_key=True, autoincrement=True)
    ramin = Column(Float)
    ramax = Column(Float)
    decmin = Column(Float)
    decmax = Column(Float)


def get_session(db_address):
    """
    Get a connection to the database.
    Returns
    -------
    session: SQLAlchemy Database Session
    """
    # Build a new engine for each session. This makes things thread safe.
    engine = create_engine(db_address, poolclass=pool.NullPool)
    Base.metadata.bind = engine

    # We don't use autoflush typically. I have run into issues where SQLAlchemy would try to flush
    # incomplete records causing a crash. None of the queries here are large, so it should be ok.
    db_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = db_session()
    return session


def create_db(db_address):
    # Create an engine for the database
    engine = create_engine(db_address)

    # Create all tables in the engine
    # This only needs to be run once on initialization.
    Base.metadata.create_all(engine)


class refcat2dbmaker():
    ''' Generate a sqlite database with rtree indexing on positions from the Tonry Atlas refact2 ascii csv
    distribution files.

    '''


    dbname = 'refcat2.db'
    # Coulmns that we will ingest into the sqlite database
    usedcolnames=['objid','RA','Dec','pmra','pmdec','g','r','i','z','dg','dr','di','dz']

    def __init__(self):
        with open('refcat2columns.dat') as f:
            columns = [word.strip() for word in f]
            self.usedindices = [columns.index(ii) for ii in self.usedcolnames]

            # Generate a database CREATE command out of the used columns.
            self.fieldsstringtpye = ""
            for field in self.usedcolnames:
                if 'objid' in field:
                    self.fieldsstringtpye = self.fieldsstringtpye + "objid INTEGER NOT NULL PRIMARY KEY"
                else:
                    self.fieldsstringtpye = self.fieldsstringtpye + ", %s FLOAT" % field


    def parse_row(self, line):
        '''
        Generate a list of values of interest out of a single line from the csv file.
        :param line:
        :return:
        '''
        values = line.rstrip().split(',')
        retval =  list( (values[index] for index in self.usedindices) )
        return retval


    def addstars(self, cursor, data):
        ''' bulk write a list of stars into the database; much faster than individual insert commands. '''

        cursor.execute('begin transaction')
        cursor.executemany ('insert into sources (%s) values (%s)' % (','.join(self.usedcolnames), ','.join('?' * len(self.usedcolnames))), data)
        cursor.execute('commit')

    def addallfromcsv(self, catalog_file, cursor):
        '''
        Add all stars from a csv ascii file into the databae file
        :param catalog_file:
        :param cursor:
        :return:
        '''
        log.info ("Starting to ingest stars from csv file %s" % catalog_file)
        nbulk = 10000

        with gzip.open(catalog_file, 'rt') as csv_file:
            ningested = 0

            starbuffer = []
            for line in csv_file:
                starbuffer.append (self.parse_row(line.rstrip()))
                ningested += 1

                if ningested % 1000000 == 0:

                    self.addstars (cursor, starbuffer)
                    print (("Number ingested: % 10d\r" %ningested ), )
                    starbuffer = []

        self.addstars (cursor, starbuffer)


    def makedb (self, catalogfiles):
        '''
        Create a data base file out of the Tonry refcat2 csv distribution.
        :param catalogfiles:
        :return:
        '''
        connection = sqlite3.connect(self.dbname)
        cursor = connection.cursor()
        cursor.execute('PRAGMA LOCKING_MODE=EXCLUSIVE;')
        cursor.execute('PRAGMA SYNCHRONOUS=OFF;')
        cursor.execute('PRAGMA journal_mode=memory;')
        cursor.execute("PRAGMA count_changes=OFF;")
        cursor.execute('PRAGMA TEMP_STORE=memory;')
        cursor.execute('PRAGMA auto_vacuum = 0;')
        cursor.execute('PRAGMA foreign_keys=OFF;')
        cursor.execute('begin transaction')
        cursor.execute('CREATE TABLE IF NOT EXISTS sources (%s);' % self.fieldsstringtpye)
        cursor.execute('COMMIT')

        for catalog in catalogfiles:
            log.info ("Adding %s" % catalog)
            self.addallfromcsv (catalog, cursor)

        log.info ("Creating rtree")
        cursor.execute('CREATE VIRTUAL TABLE if not exists positions using rtree(objid, ramin, ramax, decmin, decmax);')
        cursor.execute('insert into positions (objid, ramin, ramax, decmin, decmax) select objid, RA, RA, Dec, Dec from sources;')
        cursor.close()






dbmaker = refcat2dbmaker ()
dbmaker.makedb(glob.glob ('/home/dharbeck/Catalogs/refcat2/hlsp_atlas-refcat2_atlas_ccd_*.csv.gz'))
