#!/bin/env python

import matplotlib
import numpy

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import datetime
import sys
import math
import calendar
import scipy.signal
import argparse
import logging
import boto3
import io
import os
from itertools import cycle
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates

from longtermphotzp.photdbinterface import photdbinterface

assert sys.version_info >= (3, 5)
_logger = logging.getLogger(__name__)

airmasscorrection = {'up': 0.59, 'gp': 0.14, 'rp': 0.08, 'ip': 0.06, 'zp': 0.04, 'zs': 0.04, 'Y':0.03, 'U': 0.54, 'B': 0.23, 'V':0.12, 'R':0.09, 'Rc':0.09, 'I': 0.04}

# TODO: make this a parameter.
starttime = datetime.datetime(2016, 1, 1)

endtime = datetime.datetime.utcnow().replace(day=28) + datetime.timedelta(days=31 + 4)
endtime.replace(day=1)

colorterms = {}

# List of all telescopes to evaluate.
telescopedict = {
    'lsc': ['doma-1m0a', 'domb-1m0a', 'domc-1m0a', 'aqwa-0m4a', 'aqwb-0m4a'],
    'coj': ['clma-2m0a', 'doma-1m0a', 'domb-1m0a', 'clma-0m4a', 'clma-0m4b', 'clma-0m4c'],
    'ogg': ['clma-2m0a', 'clma-0m4b', 'clma-0m4c'],
    'elp': ['doma-1m0a', 'domb-1m0a', 'aqwa-0m4a', 'aqwb-0m4a', 'aqwb-0m4b'],
    'cpt': ['doma-1m0a', 'domb-1m0a', 'domc-1m0a', 'aqwa-0m4a'],
    'tfn': ['aqwa-0m4a', 'aqwa-0m4b', 'doma-1m0a', 'domb-1m0a'],
    #  'sqa': ['doma-0m8a'],
    #  'bpl': ['doma-1m0a']
}

# TODO: either migrate into separate file or find a better source, e.g., store in db, or query maintenance data base.

telescopecleaning = {
    'lsc-doma-1m0a': [datetime.datetime(2018, 4, 5), datetime.datetime(2018, 5, 30), datetime.datetime(2018, 7, 24),
                      datetime.datetime(2018, 8, 27), datetime.datetime(2018, 10, 24),  datetime.datetime(2019, 1, 11),
                      datetime.datetime(2019,3 , 7), datetime.datetime(2019, 4, 9), datetime.datetime(2019, 5, 15),
                      datetime.datetime(2019, 6, 27), datetime.datetime(2019, 7, 30), datetime.datetime(2019, 8, 27),
                      datetime.datetime(2020, 1, 31),   datetime.datetime(2020, 2, 21),datetime.datetime(2020, 3, 6),
                      datetime.datetime(2020, 11, 27),datetime.datetime(2020, 12, 29), datetime.datetime(2021, 1, 29),
                      datetime.datetime(2021, 2, 26),datetime.datetime(2021, 4, 6),datetime.datetime(2021, 5, 14),
                      datetime.datetime(2021, 6, 16),datetime.datetime(2021, 7, 15),datetime.datetime(2021, 8, 6),
                      datetime.datetime(2021, 9, 2),datetime.datetime(2021, 10, 12),datetime.datetime(2021, 11, 8),],

    'lsc-domb-1m0a': [datetime.datetime(2018, 4, 5), datetime.datetime(2018, 5, 30), datetime.datetime(2018, 7, 24),
                      datetime.datetime(2018, 8, 27), datetime.datetime(2018, 10, 24), datetime.datetime(2019, 11, 1),
                      datetime.datetime(2019,3 , 7), datetime.datetime(2019, 4, 9), datetime.datetime(2019, 5, 15),
                      datetime.datetime(2019, 6, 27), datetime.datetime(2019, 7, 30), datetime.datetime(2019, 8, 27),
                      datetime.datetime(2020, 1, 31),   datetime.datetime(2020, 2, 21),datetime.datetime(2020, 3, 6),
                      datetime.datetime(2020, 11, 27),datetime.datetime(2020, 12, 29), datetime.datetime(2021, 1, 29),
                      datetime.datetime(2021, 2, 26),datetime.datetime(2021, 4, 6),datetime.datetime(2021, 5, 14),
                      datetime.datetime(2021, 6, 16),datetime.datetime(2021, 7, 15),datetime.datetime(2021, 8, 6),
                      datetime.datetime(2021, 9, 2),datetime.datetime(2021, 10, 12),datetime.datetime(2021, 11, 8),],

    'lsc-domc-1m0a': [datetime.datetime(2017, 8, 31), datetime.datetime(2018, 4, 5), datetime.datetime(2018, 5, 30),
                      datetime.datetime(2018, 7, 24), datetime.datetime(2018, 9, 14),
                      datetime.datetime(2018, 10, 24), datetime.datetime(2019, 11, 1),datetime.datetime(2019,3 , 7),
                      datetime.datetime(2019, 4, 9), datetime.datetime(2019, 5, 15),
                      datetime.datetime(2019, 6, 27), datetime.datetime(2019, 7, 30), datetime.datetime(2019, 8, 27),
                      datetime.datetime(2020, 1, 31),   datetime.datetime(2020, 2, 21),datetime.datetime(2020, 3, 6),
                      datetime.datetime(2020, 11, 27),datetime.datetime(2020, 12, 29), datetime.datetime(2021, 1, 29),
                      datetime.datetime(2021, 2, 26),datetime.datetime(2021, 4, 6),datetime.datetime(2021, 5, 14),
                      datetime.datetime(2021, 6, 16),datetime.datetime(2021, 7, 15),datetime.datetime(2021, 8, 6),
                      datetime.datetime(2021, 9, 2),datetime.datetime(2021, 10, 12),datetime.datetime(2021, 11, 8),],
    'lsc-aqwa-0m4a': [datetime.datetime(2018, 4, 17), datetime.datetime(2018, 9, 20), ],
    'lsc-aqwb-0m4a': [datetime.datetime(2018, 4, 17), datetime.datetime(2018, 9, 20), ],
    'coj-clma-0m4a': [datetime.datetime(2017, 6, 30), datetime.datetime(2019, 4, 4), ],
    'coj-clma-0m4b': [datetime.datetime(2017, 6, 30), datetime.datetime(2019, 4, 4), ],
    'coj-clma-0m4c': [datetime.datetime(2021, 10, 15), ],
    'coj-clma-2m0a': [datetime.datetime(2018, 6, 20), ],
    'coj-doma-1m0a': [datetime.datetime(2018, 6, 18), datetime.datetime(2019, 4, 3), datetime.datetime(2019, 7, 17), ],
    'coj-domb-1m0a': [datetime.datetime(2018, 6, 10), datetime.datetime(2019, 3, 25), ],
    'elp-clma-0m4a': [datetime.datetime(2019, 5, 29), ],
    'elp-doma-1m0a': [datetime.datetime(2017, 9, 20), datetime.datetime(2018, 4, 5), datetime.datetime(2018, 5, 6),
                      datetime.datetime(2018, 6, 9), datetime.datetime(2018, 12, 11), ],
    'ogg-clma-2m0a': [datetime.datetime(2017, 10, 20), ],

    'cpt-doma-1m0a': [datetime.datetime(2017, 11, 15), datetime.datetime(2018, 9, 13), datetime.datetime(2018, 10, 24),
                      ],
    'cpt-domb-1m0a': [datetime.datetime(2017, 11, 15), datetime.datetime(2018, 9, 13), datetime.datetime(2018, 10, 24),
                      ],
    'cpt-domc-1m0a': [datetime.datetime(2017, 11, 15), datetime.datetime(2018, 9, 13), datetime.datetime(2018, 10, 24),
                      ],
    'tfn-aqwa-0m4a': [datetime.datetime(2018, 9, 12), datetime.datetime(2021, 7, 16), ],
    'tfn-aqwa-0m4b': [datetime.datetime(2018, 9, 12), datetime.datetime(2021, 7, 16), ],
    'tfn-doma-1m0a': [datetime.datetime(2021, 11, 12), datetime.datetime(2021, 11, 24), datetime.datetime(2021, 12, 7),
                      datetime.datetime(2022, 1, 4), ],
    'tfn-domb-1m0a': [datetime.datetime(2021, 11, 12), datetime.datetime(2021, 11, 24), datetime.datetime(2021, 12, 7),
                      datetime.datetime(2022, 1, 4), ],
}

# List of events when the telesocope mirror was changed.
# in practice, program will attempt to do a fit between dates listed here. so it does not matter what triggered
# the new slope calculation
mirrorreplacmenet = {

    'ogg-clma-0m4b': [datetime.datetime(2024, 2, 1),],

    'ogg-clma-0m4c': [datetime.datetime(2022, 7, 1),],

    'ogg-clma-2m0a': [datetime.datetime(2016, 4, 1),
                      datetime.datetime(2017, 10, 20),
                      datetime.datetime(2019, 6, 16),# this was a mirror wash only
                      datetime.datetime(2020, 9, 27), # Transition to Muscat3
                      datetime.datetime(2021, 3, 15), # Transition to Muscat3 ep01 -> ep05
                      ],

    'elp-aqwa-0m4a': [datetime.datetime(2023, 6, 1),],

    'elp-doma-1m0a': [datetime.datetime(2016, 4, 1),
                      datetime.datetime(2018, 4, 5),
                      datetime.datetime(2019, 5, 22),  # mirror wash
                      datetime.datetime(2019, 10, 20),  # mirror wash
                      datetime.datetime(2020, 8, 22),  # mirror wash
                      datetime.datetime(2022, 7, 1),  # mirror wash
                      ],
    'elp-domb-1m0a': [datetime.datetime(2019, 10, 20),  # mirror wash
                      datetime.datetime(2020, 8, 19),  # mirror wash
                      datetime.datetime(2022, 7, 1),  # mirror wash
                      ],

    'coj-clma-2m0a': [datetime.datetime(2016, 4, 1),
                      datetime.datetime(2018, 6, 20),
                      datetime.datetime(2021, 2, 20),
                      datetime.datetime(2022, 10, 15),
                      datetime.datetime(2023, 10, 18), # Muscat 4 installation
                      ],

    'coj-clma-0m4a': [datetime.datetime(2023, 10, 1),],

    'coj-clma-0m4b': [datetime.datetime(2023, 10, 1),],

    'coj-doma-1m0a': [datetime.datetime(2016, 10, 1),
                      datetime.datetime(2018, 6, 18),
                      datetime.datetime(2020, 2, 20), ],
    'coj-domb-1m0a': [datetime.datetime(2016, 10, 1),
                      datetime.datetime(2018, 6, 10),
                      datetime.datetime(2020, 2, 26),
                      ],

    'lsc-aqwa-0m4a': [datetime.datetime(2024, 3, 15),],

    'lsc-aqwb-0m4a': [datetime.datetime(2024, 3, 15),],

    'lsc-doma-1m0a': [datetime.datetime(2016, 6, 1),
                      datetime.datetime(2016, 10, 15),
                      datetime.datetime(2018, 9, 14),
                      datetime.datetime(2022, 11, 1),], # mirror wash only
    'lsc-domb-1m0a': [datetime.datetime(2016, 4, 1),
                      datetime.datetime(2018, 9, 14),
                      datetime.datetime(2022, 11, 1),], # mirror wash only
    'lsc-domc-1m0a': [datetime.datetime(2016, 4, 1),
                      datetime.datetime(2017, 8, 31),
                      datetime.datetime(2018, 9, 14),
                      datetime.datetime(2022, 11, 1),], # mirror wash only

    'cpt-aqwa-0m4a': [datetime.datetime(2023, 5, 1),],

    'cpt-doma-1m0a': [datetime.datetime(2016, 10, 1),
                      datetime.datetime(2016, 11, 1),
                      datetime.datetime(2018, 10, 24),
                      datetime.datetime(2019, 9, 22),  # mirror wash, no replacement
                      datetime.datetime(2023, 1, 15), # wet mirror wash
                      ],
    'cpt-domb-1m0a': [datetime.datetime(2016, 10, 1),
                      datetime.datetime(2018, 10, 24),
                      datetime.datetime(2019, 9, 22),  # mirror wash, no replacement
                      datetime.datetime(2023, 1, 15), # wet mirror wash
                      ],
    'cpt-domc-1m0a': [datetime.datetime(2016, 10, 1),
                      datetime.datetime(2018, 10, 24),
                      datetime.datetime(2019, 9, 22),  # mirror wash, no replacement
                      datetime.datetime(2023, 1, 15), # wet mirror wash
                      ],

    'tfn-aqwa-0m4a' : [datetime.datetime(2023, 11, 1),
                       ], # delta rho replacement
    'tfn-aqwa-0m4b' : [datetime.datetime(2023, 11, 1),
                       ], # delta rho replacement
    'tfn-doma-1m0a' : [datetime.datetime(2021, 5, 1),
                       datetime.datetime(2023, 11, 15),
                       ], # delta rho replacement
    'tfn-domb-1m0a' : [datetime.datetime(2021, 5, 1),
                       datetime.datetime(2023, 11, 15),
                       ], # delta rho replacement




}

telescopereferencethroughput = {'up':{"1m0": 22.45, "2m0": 21.4,  '0m4':  17.50},
                                'gp':{"1m0": 24.3,  "2m0": 25.4,  '0m4':  21.8},
                                'rp':{"1m0": 23.8,  "2m0": 25.35, '0m4':  21.2},
                                'ip':{"1m0": 23.5,  "2m0": 25.5,  '0m4':  20.1},
                                'zp':{"1m0": 22.2,  "2m0": 24.3,  '0m4':  18.4},
                                'Y': {"1m0": 20.40, "2m0": 21.4,  '0m4': 17.8},
                                'U': {"1m0": 21.4,  "2m0": 21.3,  '0m4': 18.0},
                                'B': {"1m0": 23.5,  "2m0": 24.4,  '0m4': 21.4},
                                'V': {"1m0": 23.5,  "2m0": 24.6,  '0m4': 21.4},
                                'R': {"1m0": 23.8,  "2m0": 24.9,  '0m4': 21.2},
                                'I': {"1m0": 23.2,  "2m0": 24.1,  '0m4': 20.3},}


def aws_enabled():
    '''Return True if AWS support is configured'''
    access_key = os.environ.get('AWS_ACCESS_KEY_ID', None)
    secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY', None)
    s3_bucket = os.environ.get('AWS_S3_BUCKET', None)
    region = os.environ.get('AWS_DEFAULT_REGION', None)

    return access_key and secret_key and s3_bucket and region


def write_to_storage_backend(directory, filename, data):
    if aws_enabled():
        # AWS S3 Bucket upload
        client = boto3.client('s3')
        bucket = os.environ.get('AWS_S3_BUCKET', None)
        with io.BytesIO(data) as fileobj:
            _logger.debug(f'Write data to AWS S3: {bucket}/{filename}')
            response = client.upload_fileobj(fileobj, bucket, filename)
            return response
    else:
        fullpath = os.path.join(directory, filename)
        with open(fullpath, 'wb') as fileobj:
            fileobj.write(data)
            return True


def getCombineddataByTelescope(site, telescope, context, instrument=None, filter = None, cacheddb=None):
    """
    Concatenate all zeropoint data for a site, and select by telescope and instrument.
    :param site:
    :param telescope: string slecting dome *& telescope: 'domb:1m0a'
    :param context:
    :param instrument:
    :return: concatenated data for a site / tel / isntrument selection.
    """

    if cacheddb is None:
        db = photdbinterface(context.database)
    else:
        db = cacheddb
    _logger.info("Getting all photometry data for %s %s %s" % (site, telescope, instrument))
    dome, tel = telescope.split("-")

    results = db.readRecords(site, dome, tel, instrument, filter=filter)
    if cacheddb is None:
        db.close()
    return results


def dateformat(starttime, endtime):
    """ Utility to prettify a plot with dates.
    """

    plt.xlim([starttime, endtime])
    plt.gcf().autofmt_xdate()
    years = mdates.YearLocator()  # every year
    months = mdates.MonthLocator(bymonth=[4, 7, 10])  # every month
    yearsFmt = mdates.DateFormatter('%Y %b')
    monthformat = mdates.DateFormatter('%b')
    plt.gca().xaxis.set_major_locator(years)
    plt.gca().xaxis.set_major_formatter(yearsFmt)
    plt.gca().xaxis.set_minor_locator(months)
    plt.gca().xaxis.set_minor_formatter(monthformat)
    plt.setp(plt.gca().xaxis.get_minorticklabels(), rotation=45)
    plt.setp(plt.gca().xaxis.get_majorticklabels(), rotation=45)
    plt.gca().grid(which='minor')


def plotlongtermtrend(select_site, select_telescope, select_filter, context, instrument=None, cacheddb=None):
    filenames = []
    filters = None
    if select_filter is not None:
        if (select_filter == 'zp') or (select_filter == 'zs'):
            filters = ['zs','zp']
        else:
            filters= [select_filter,]


    data = getCombineddataByTelescope(select_site, select_telescope, context, instrument, filter=filters, cacheddb=cacheddb)

    mystarttime = starttime
    # if (select_site == 'elp') and (select_telescope=='doma-1m0a'):
    #    mystarttime = datetime.datetime(2014, 1, 1)

    if data is None:
        return
    # down-select data by viability and camera / filer combination
    selection = np.ones(len(data['name']), dtype=bool)

    if select_filter is not None:
        if (select_filter == 'zp') or (select_filter == 'zs'):
            selection = selection &  numpy.logical_or( (data['filter'] == 'zs') , (data['filter'] == 'zp'))
        elif  (select_filter == 'R') or (select_filter == 'Rc'):
            selection = selection &  ( (data['filter'] == 'Rc') | (data['filter'] == 'R'))
        else:
            selection = selection & (data['filter'] == select_filter)
    if instrument is not None:
        selection = selection & (data['camera'] == instrument)

    # weed out bad data
    selection = selection & np.logical_not(np.isnan(data['zp']))
    selection = selection & np.logical_not(np.isnan(data['airmass']))

    if len(selection) == 0:
        _logger.warning("No data points left after down selection. Not wasting time on empty plots.")
        return

    zpselect = data['zp'][selection]
    dateselect = data['dateobs'][selection]
    airmasselect = data['airmass'][selection]
    cameraselect = data['camera'][selection]
    zpsigselect = data['zpsig'][selection]

    ymax = 25.5  # good starting point for 2m:spectral cameras
    photzpmaxnoise = 0.2
    if select_telescope is not None:

        if '0m4' in select_telescope:  # 0.4m sbigs
            ymax = 22.5
            if  'up' in select_filter:
                ymax = 20
            photzpmaxnoise = 0.5

        if select_filter in telescopereferencethroughput:
            ymax = telescopereferencethroughput[select_filter][select_telescope[-4:-1]] +1

    # Calculate air-mass corrected photometric zeropoint; corrected to airmass of 1
    zp_air = zpselect + airmasscorrection[select_filter] * airmasselect - airmasscorrection[select_filter]

    # find the overall trend of zeropoint variations, save to output file.
    if len(dateselect[zpsigselect < photzpmaxnoise]) > 0:
        _x, _y = findUpperEnvelope(dateselect[zpsigselect < photzpmaxnoise], zp_air[zpsigselect < photzpmaxnoise],
                                   ymax=ymax)
        db = photdbinterface(context.database) if cacheddb is None else cacheddb
        db.storemirrormodel("%s-%s" % (select_site, select_telescope), select_filter, _x, _y)
        if cacheddb is None:
            db.close()
    else:
        _x = None
        _y = None



    # now we are starting to plot stuff

    plt.figure()

    plot_referencethoughput(mystarttime, endtime, select_filter, select_telescope[-4:-1])
    # mark mirror cleaning events.
    for telid in telescopecleaning:
        _site, _enc, _tel = telid.split("-")

        if (_site == select_site) and (select_telescope == '%s-%s' % (_enc, _tel)):
            for event in telescopecleaning[telid]:
                plt.axvline(x=event, color='grey', linestyle=':')

    for telid in mirrorreplacmenet:
        _site, _enc, _tel = telid.split("-")

        if (_site == select_site) and (select_telescope == '%s-%s' % (_enc, _tel)):
            for event in mirrorreplacmenet[telid]:
                plt.axvline(x=event, color='orange', linestyle='--')

    #  plot all the zeropoint measurements, but label different cameras differently.
    uniquecameras = np.unique(cameraselect)

    for uc in uniquecameras:
        plt.plot(dateselect[(zpsigselect <= photzpmaxnoise) & (cameraselect == uc)],
                 zp_air[(zpsigselect <= photzpmaxnoise) & (cameraselect == uc)],
                 'o', markersize=2, label=uc)
        plt.plot(dateselect[zpsigselect > photzpmaxnoise], zp_air[zpsigselect > photzpmaxnoise], '.',
                 markersize=1, c="grey", label='_nolegend_')

    if _x is not None:
        plt.plot(_x, _y, "-", c='red', label='upper envelope')

        for telid in mirrorreplacmenet:
            _site, _enc, _tel = telid.split("-")
            if (_site == select_site) and (select_telescope == '%s-%s' % (_enc, _tel)):

                events = mirrorreplacmenet[telid]
                events.append(datetime.datetime.utcnow())
                print(events)
                for ii in range(len(events) - 1):
                    start = mirrorreplacmenet[telid][ii]
                    end = mirrorreplacmenet[telid][ii + 1]
                    fittrendtomirrormodel(_x, _y, start, end, plot=True)

    else:
        _logger.warning("Mirror model failed to compute. not plotting !")

    # prettify, decorations, etc
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    plt.ylim([ymax - 4.5, ymax])
    dateformat(mystarttime, endtime)
    plt.xlabel("DATE-OBS")
    plt.ylabel("Photometric Zeropoint %s" % select_filter)
    plt.title("Long term throughput  %s:%s in %s" % (select_site, select_telescope, select_filter))
    plt.gcf().set_size_inches(12, 6)
    # and finally safe the plot.
    with io.BytesIO() as fileobj:
        plt.savefig(fileobj, format='png', bbox_inches='tight')
        plt.close()

        filename = 'photzptrend-{}-{}-{}.png'.format(select_site, select_telescope, select_filter)
        filenames.append(filename)
        write_to_storage_backend(context.imagedbPrefix, filename, fileobj.getvalue())

    # for internal use: generate error plots.
    if context.errorhistogram:
        plt.figure()
        plt.hist(zpsigselect, 50, range=[0, 1], normed=True)

        with io.BytesIO() as fileobj:
            plt.savefig(fileobj, format='png')
            plt.close()

            filename = 'errorhist-%s-%s-%s.png'.format(select_site, select_telescope, select_filter)
            filenames.append(filename)
            write_to_storage_backend(context.imagedbPrefix, filename, fileobj.getvalue())

    # plot airmass vs zeropoint as a sanity check tool
    plt.figure()
    plt.plot(airmasselect, zpselect, ".", c="grey")
    plt.plot(airmasselect, zp_air, ".", c="blue")
    plt.xlabel("Airmass")
    plt.ylabel("Photomertic Zeropoint %s" % select_filter)
    plt.title("Global airmass trend and correction check")
    meanzp = np.nanmedian(zpselect)
    if math.isfinite(meanzp):
        plt.ylim([meanzp - 0.5, meanzp + 0.5])
    else:
        plt.ylim ([20,26])
    with io.BytesIO() as fileobj:
        plt.savefig(fileobj, format='png')
        plt.close()

        filename = 'airmasstrend-{}-{}-{}.png'.format(select_site, select_telescope, select_filter)
        filenames.append(filename)
        write_to_storage_backend(context.imagedbPrefix, filename, fileobj.getvalue())

    # Color terms
    plt.figure()
    selection = selection & np.logical_not(np.isnan(data['colorterm']))
    selection = selection & (np.abs(data['colorterm']) < 0.3)
    selection_lonoise = selection & (data['zpsig'] < 0.2)
    selection_hinoise = selection & (data['zpsig'] >= 0.2)

    plt.plot(data['dateobs'][selection_hinoise], data['colorterm'][
        selection_hinoise], '.', markersize=2, c="grey",
             label="color term [ hi sigma] %s " % select_filter)
    colortermselect = data['colorterm'][selection_lonoise]
    dateselect = data['dateobs'][selection_lonoise]
    meancolorterm = np.median(colortermselect)
    plt.plot(dateselect, colortermselect, 'o', markersize=2, c="blue",
             label="color term [low sigma] %s " % select_filter)


    plt.axhline(y=meancolorterm, color='r', linestyle='-', label=f"median color term: {meancolorterm:5.2f}")
    _logger.info("Color term in filter %s : % 5.3f" % (select_filter, meancolorterm))
    plt.legend()
    # store the color terms
    if select_filter not in colorterms:
        colorterms[select_filter] = {}
    colorterms[select_filter][f'{select_site}-{select_telescope}'] = meancolorterm

    dateformat(mystarttime, endtime)
    plt.ylim([-0.2, 0.2])

    plt.title("Color term (g-r)  %s:%s in %s" % (select_site, select_telescope, select_filter))
    plt.xlabel("DATE-OBS")
    plt.ylabel("Color term coefficient (g-r)")
    with io.BytesIO() as fileobj:
        plt.savefig(fileobj, format='png')
        plt.close()

        filename = 'colortermtrend-{}-{}-{}.png'.format(select_site, select_telescope, select_filter)
        filenames.append(filename)
        write_to_storage_backend(context.imagedbPrefix, filename, fileobj.getvalue())

    # thats it, some day please refactor(select_filter, this into smaller chunks.

    return filenames



def plot_referencethoughput(start, end, select_filter, select_telescope):
    filterinreflux = select_filter in telescopereferencethroughput
    _logger.info("filter %s  in referenceflux table %s" % (select_filter, filterinreflux))
    if not filterinreflux:
        return

    telescopeinreflux = select_telescope in telescopereferencethroughput[select_filter]
    _logger.info("telescope %s in reference flux table: %s" % (select_telescope, telescopeinreflux))

    if filterinreflux and telescopeinreflux:
        goodvalue = telescopereferencethroughput[select_filter][select_telescope]
        rect = Rectangle((start, goodvalue), end - start, -0.2, color='#A0FFA0A0')
        plt.axes().add_patch(rect)

def findUpperEnvelope(dateobs, datum, ymax=24.2):
    """
    Find the upper envelope of a photZP time line

    Idea:
    For a set of day(s), find the highest n zeropoint measurements within an error range.
    Omit the brightest one for outlier rejection. Average the remaining data points of the day. Accept as value

    After this, filter value. Currently, I use a cheap-o-Kalman fake with a fixed Kalman gain. Not smart, but works

    Reject some bright and too faint outliers, i.e., if Kalman correction is too large, reject as an obvious large issue.


    :param dateobs:
    :param datum:
    :param range:
    :return:
    """

    stderror = 0.03

    alldata = zip(dateobs, datum)
    sorted_points = sorted(alldata)
    x = np.asarray([point[0] for point in sorted_points])
    y = np.asarray([point[1] for point in sorted_points])

    day_x = []
    day_y = []

    # TODO: define  day / night boundary for the site.
    startdate = datetime.datetime(year=x[0].year, month=x[0].month,
                                  day=x[0].day, hour=12)
    enddate = x[len(x) - 1]
    while startdate < enddate:
        # Calculate the best throughput of a day
        todayzps = y[
            (x > startdate) & (x < startdate + datetime.timedelta(days=1)) & (
                    y < ymax) & (y is not np.nan)]

        if len(todayzps) > 3:  # require a minimum amount of data for a night

            todayzps = np.sort(todayzps)[1:]
            maxzp = np.nanmax(todayzps)
            upperEnv = np.nanmean(todayzps[todayzps > (maxzp - stderror)])

            if upperEnv is not np.nan:
                day_x.append(startdate)
                day_y.append(upperEnv)

        startdate = startdate + datetime.timedelta(days=1)

    # filter the daily zero point variation. Work in progress.
    medianrange = 9
    newday_y = scipy.signal.medfilt(day_y, medianrange)

    return np.asarray(day_x), newday_y


def trendcorrectthroughput(datadate, datazp, modeldate, modelzp):
    """ Detrend input data based in a trend model

    """

    modelgmt = np.zeros((len(modeldate)))
    for ii in range(0, len(modeldate)):
        modelgmt[ii] = calendar.timegm(modeldate[ii].timetuple())

    corrected = np.zeros(len(datazp))
    for ii in range(0, len(corrected)):
        interpolated = np.interp(calendar.timegm(datadate[ii].timetuple()),
                                 modelgmt, modelzp)
        corrected[ii] = datazp[ii] - interpolated

    # estimate if photometric

    photomerticthres = 0.25
    day_x = []
    day_y = []
    alldata = zip(datadate, corrected)
    sorted_points = sorted(alldata)
    x = np.asarray([point[0] for point in sorted_points])
    y = np.asarray([point[1] for point in sorted_points])
    startdate = datetime.datetime(year=2016, month=4, day=1, hour=16)
    enddate = x[len(x) - 1]

    while startdate < enddate:
        todayzps = y[
            (x > startdate) & (x < startdate + datetime.timedelta(days=1))]

        photometric = -1

        if len(todayzps) > 0:  # require a minium amount of data for a night

            if np.min(todayzps > -0.15):
                photometric = 1
            else:
                photometric = 0

        day_x.append(startdate)
        day_y.append(photometric)

        startdate = startdate + datetime.timedelta(days=1)

    day_x = np.asarray(day_x)
    day_y = np.asarray(day_y)
    unclassified = len(day_y[day_y < 0])
    photometric = len(day_y[day_y > 0])
    nonphot = len(day_y[day_y == 0])
    #

    # print ("out of %d days\nphotometric\t%d\nnon-photometric\t%d\nunknown\t%d" %
    #        (unclassified+photometric+nonphot, photometric, nonphot, unclassified))

    return corrected, day_x, day_y


def fittrendtomirrormodel(dates, zps, start, end, order=1, plot=False):
    _logger.info("Calculating trend line between %s and %s " % (start, end))

    poly = np.poly1d([0, 0])

    try:
        select = (dates > start)
        select = select & (dates < end)
        _x = dates[select]
        _xx = mdates.date2num(_x)
        _y = zps[select]
        poly = np.poly1d(np.polyfit(_xx, _y, order))
        _logger.info("Slope calculated to % 5.3f mag / month" % (poly.c[0] * 30))

        if plot:
            _y = poly(_xx)
            plt.plot(_x, _y, "--", label="% 5.3f mag \nper month" % (poly.c[0] * 30))
    except:
        _logger.error("While fitting phzp trend; probably not enough data points.")

    return poly



def plot_all_color_terms (context, colorterms, type='1m0'):
    filter = next(iter(colorterms))
    myterms = colorterms[filter]
    data = list(myterms.items())
    data = np.array(data).T


    good = ['1m0' in x for x in data[0]]
    xTicks = data[0] [good]
    y =  (data[1].astype(float))[good]
    x = np.arange(len(xTicks)) +1
    plt.xticks(x, xTicks, rotation=45)
    plt.plot (x,y,'*')
    plt.ylim ([-0.2,0.2])
    plt.title(f"1m0a Color terms {filter} vs (g-r)")
    plt.ylabel("Color term")

    with io.BytesIO() as fileobj:
        # create the plot into an in-memory Fileobj
        plt.gcf().set_size_inches(12, 6)
        plt.savefig(fileobj, format='png', bbox_inches='tight')
        plt.close()

        # save the plot onto stable storage
        filename = 'colorterms_{}.png'.format( context.filter)

        write_to_storage_backend(context.imagedbPrefix, filename, fileobj.getvalue())


def plotallmirrormodels(context, type=['2m0a', '1m0a'], range=[22.5, 25.5], cacheddb=None):
    '''
    Fetch mirror model from database for a selected class of telescopes, and
    put them all into one single plot.

    Returns a list of figure names (S3 keys)
    '''
    filenames = []

    if cacheddb is None:
        db = photdbinterface(context.database)
    else:
        db = cacheddb

    myfilter = context.filter
    modellist = []

    for t in type:
        modellist.extend(db.findmirrormodels(t, myfilter))
        plot_referencethoughput(starttime, endtime, myfilter, t[0:3])

    modellist.sort(key=lambda x: x[0:3] + x[-1:-5].replace('2', '0') + x[4:8])
    _logger.info("Plotting several models in a single plot. These are the models returned from search %s: %s" % (
        type, modellist))

    plt.rc('lines', linewidth=1)
    prop_cycle = cycle(['-', '-.'])

    for model in modellist:
        _logger.debug("Plotting mirror model %s" % model)
        data = db.readmirrormodel(model, myfilter)
        plt.gcf().autofmt_xdate()
        plt.plot(data['dateobs'], data['zp'], next(prop_cycle), label=model.replace('-', ':'), )

    plt.legend(bbox_to_anchor=(1.01, 1), loc='upper left', ncol=1)
    plt.xlabel('DATE-OBS')
    plt.ylabel("phot zeropoint %s" % myfilter)
    dateformat(starttime, endtime)
    plt.ylim(range)
    plt.title("Photometric zeropoint model in filter %s" % myfilter)
    plt.grid(True, which='both')

    name = ""
    for ii in type:
        name += str(ii)

    with io.BytesIO() as fileobj:
        # create the plot into an in-memory Fileobj
        plt.gcf().set_size_inches(12, 6)
        plt.savefig(fileobj, format='png', bbox_inches='tight')
        plt.close()

        # save the plot onto stable storage
        filename = 'allmodels_{}_{}.png'.format(name, context.filter)
        filenames.append(filename)
        write_to_storage_backend(context.imagedbPrefix, filename, fileobj.getvalue())

    if cacheddb is None:
        db.close()

    return filenames


def renderHTMLPage(context, filenames):
    _logger.info("Now rendering output html page")

    message = """<html>
<head></head>
<body><title>LCO Zeropoint Plots</title>
"""
    message += "<p/>Figures updated %s UTC <p/>\n" % (datetime.datetime.utcnow())
    message += """
<h1> Overview </h1>
     <a href="allmodels_2m01m0_rp.png"><img src="allmodels_2m01m0_rp.png" width="800" /></a>
     <a href="allmodels_0m4_rp.png"><img src="allmodels_0m4_rp.png" width="800" /></a>
    <p/>

<h1> Details by Site: </h1>
"""

    for site in telescopedict:
        message = message + " <h2> %s </h2>\n" % (site)

        zptrendimages = [k for k in filenames if k.startswith('photzptrend')]
        zptrendimages.sort(key=lambda x: x[-16: -4])

        _logger.debug(
            "Found individual telescopes zp trend plots for site %s to include:\n\t %s " % (site, zptrendimages))

        for zptrend in zptrendimages:
            line = '<a href="%s"><img src="%s" height="450"/></a>  <img src="%s" height="450"/>  <img src="%s" height="450"/><p/>' % (
                zptrend, zptrend, zptrend.replace('photzptrend', 'colortermtrend'),
                zptrend.replace('photzptrend', 'airmasstrend'))
            message = message + line

    message = message + "</body></html>"

    with io.BytesIO() as fileobj:
        fileobj.write(message.encode('utf-8'))

        filename = 'index.html'
        write_to_storage_backend(context.imagedbPrefix, filename, fileobj.getvalue())


def parseCommandLine():
    """ Read command line parameters
    """

    parser = argparse.ArgumentParser(
        description='Calculate long-term trends in photometric database.')

    parser.add_argument('--log_level', dest='log_level', default='INFO', choices=['DEBUG', 'INFO'],
                        help='Set the debug level')

    parser.add_argument('--outputdirectory', dest='imagedbPrefix', default='~/lcozpplots',
                        help='Directory containing photometryc databases')
    parser.add_argument('--database', default='~/lcozpplots/lcophotzp.db')
    parser.add_argument('--site', dest='site', default=None, help='sites code for camera')
    parser.add_argument('--telescope', default=None,
                        help='Telescope id. written inform enclosure-telescope, e.g., "domb-1m0a"')
    parser.add_argument('--filter', default='rp', help='Which filter to process.', choices=['up', 'gp', 'rp', 'ip', 'zp','zs', 'Y', 'U', 'B','R','V','I'])
    parser.add_argument('--pertelescopeplots', type=bool, default=True)
    parser.add_argument('--createsummaryplots', type=bool, default=True)
    parser.add_argument('--renderhtml', type=bool, default=True)
    parser.add_argument('--errorhistogram', type=bool, default=False)

    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper()),
                        format='%(asctime)s.%(msecs).03d %(levelname)7s: %(module)20s: %(message)s')

    args.imagedbPrefix = os.path.expanduser(args.imagedbPrefix)
    args.database = os.path.expanduser(args.database)

    return args


def longtermphotzp():
    plt.style.use('ggplot')
    matplotlib.rcParams['savefig.dpi'] = 300
    matplotlib.rcParams['figure.figsize'] = (8.0, 6.0)

    filenames = []
    args = parseCommandLine()

    if args.site is not None:
        crawlsites = [args.site, ]
    else:
        crawlsites = telescopedict

    if args.pertelescopeplots:
        db = photdbinterface(args.database)

        for site in crawlsites:
            if args.telescope is None:
                crawlScopes = telescopedict[site]
            else:
                crawlScopes = [args.telescope, ]

            for telescope in crawlScopes:
                _logger.info(
                    "Now plotting and fitting mirror model for %s %s in filter %s" % (site, telescope, args.filter))
                result = plotlongtermtrend(site, telescope, args.filter, args, cacheddb=db)
                if result is not None:
                    filenames += result

        db.close()

    # Generate mirror model plots for all telscopes in a single plot
    if args.createsummaryplots:
        filenames += plotallmirrormodels(args, type=['2m0', '1m0'])
        filenames += plotallmirrormodels(args, type=['0m4'], range=[20, 23])

    plot_all_color_terms(args, colorterms)

    # Make a fancy HTML page
    if args.renderhtml:
        renderHTMLPage(args, filenames)

    print (colorterms)
    sys.exit(0)


if __name__ == '__main__':
    longtermphotzp()

