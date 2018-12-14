import sqlite3
from sqlalchemy import Column, Integer, Float, create_engine, pool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
import gzip

log = logging.getLogger(__name__)


Base = declarative_base()
class Star(Base):
    __tablename__ = 'sources'
    objid = Column(Integer, primary_key=True, autoincrement=True)
    RA = Column(Float)
    Dec = Column(Float)
    plx = Column(Float)
    pmra = Column(Float)
    pmdec = Column(Float)

    psgmag = Column(Float)
    psrmag = Column(Float)
    psimag = Column(Float)
    pszmag = Column(Float)

    psgmagerr = Column(Float)
    psrmagerr = Column(Float)
    psimagerr = Column(Float)
    pszmagerr = Column(Float)

    jmag = Column(Float)
    hmag = Column(Float)

    jmagerr = Column(Float)
    hmagerr = Column(Float)



class Position(Base):
    __tablename__ = 'positions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ramin = Column(Float)
    ramax = Column(Float)
    decmin = Column(Float)
    decmax = Column(Float)



def parse_row(line, indicies):
    values = line.split(',')
    return (values[index] for index in indicies)

def parse_csv(catalog_file):

    with open('refcat2columns.dat') as f:
        columns = [word.strip() for word in f]


    with gzip.open(catalog_file, 'rt') as csv_file:
        for line in csv_file:




parse_csv ('/home/dharbeck/Catalogs/refcat2/hlsp_atlas-refcat2_atlas_ccd_m15-p19_multi_v1_cat.csv.gz')