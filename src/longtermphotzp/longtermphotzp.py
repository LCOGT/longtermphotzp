import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import datetime
import sys
import calendar
import scipy.signal
import argparse
import logging
import glob
import os
from itertools import cycle
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates

from photdbinterface import photdbinterface

assert sys.version_info >= (3,5)
_logger = logging.getLogger(__name__)

airmasscorrection = {'gp': 0.17, 'rp': 0.09, 'ip': 0.06, 'zp': 0.05, }

# TODO: make this a parameter.
starttime = datetime.datetime(2016, 1, 1)

endtime = datetime.datetime.utcnow().replace(day=28) + datetime.timedelta(days=31+4)
endtime.replace(day =1)

colorterms = {}

# List of all telescopes to evaluate.
telescopedict = {
    'lsc': ['doma-1m0a', 'domb-1m0a', 'domc-1m0a', 'aqwa-0m4a', 'aqwb-0m4a'],
    'coj': ['clma-2m0a', 'doma-1m0a', 'domb-1m0a', 'clma-0m4a', 'clma-0m4b'],
    'ogg': ['clma-2m0a', 'clma-0m4b', 'clma-0m4c'],
    'elp': ['doma-1m0a', 'aqwa-0m4a'],
    'cpt': ['doma-1m0a', 'domb-1m0a', 'domc-1m0a', 'aqwa-0m4a'],
    'tfn': ['aqwa-0m4a', 'aqwa-0m4b'],
    #  'sqa': ['doma-0m8a'],
    #  'bpl': ['doma-1m0a']
}

# TODO: either migrate into separate file or find a better source, e.g., store in db, or query maintenace data base.

telescopecleaning = {
    'lsc-doma-1m0a': [datetime.datetime(2018, 4, 5), datetime.datetime(2018, 5, 30),datetime.datetime(2018, 7, 24),
                      datetime.datetime(2018, 8, 27),datetime.datetime(2018, 10, 24),],
    'lsc-domb-1m0a': [datetime.datetime(2018, 4, 5), datetime.datetime(2018, 5, 30),datetime.datetime(2018, 7, 24),
                      datetime.datetime(2018, 8, 27),datetime.datetime(2018, 10, 24),],
    'lsc-domc-1m0a': [datetime.datetime(2017, 8, 31), datetime.datetime(2018, 4, 5),datetime.datetime(2018, 5, 30),
                      datetime.datetime(2018, 7, 24), datetime.datetime(2018, 9, 14),datetime.datetime(2018, 10, 24), ],
    'lsc-aqwa-0m4a': [datetime.datetime(2018, 4, 17), datetime.datetime(2018, 9, 20),],
    'lsc-aqwb-0m4a': [datetime.datetime(2018, 4, 17), datetime.datetime(2018, 9, 20),],
    'coj-clma-0m4a': [datetime.datetime(2017, 6, 30),],
    'coj-clma-0m4b': [datetime.datetime(2017, 6, 30),],
    'coj-clma-2m0a': [datetime.datetime(2018, 6, 20),],
    'coj-doma-1m0a': [datetime.datetime(2018, 6, 18),],
    'coj-domb-1m0a': [datetime.datetime(2018, 6, 10),],
    'elp-doma-1m0a': [datetime.datetime(2017, 9, 20), datetime.datetime(2018, 4, 5),datetime.datetime(2018, 5, 6), ],
    'ogg-clma-2m0a': [datetime.datetime(2017, 10,20),],
    'cpt-doma-1m0a': [datetime.datetime(2017, 11, 15),datetime.datetime(2018, 9, 13),],
    'cpt-domb-1m0a': [datetime.datetime(2017, 11, 15),datetime.datetime(2018, 9, 13),],
    'cpt-domc-1m0a': [datetime.datetime(2017, 11, 15),datetime.datetime(2018, 9, 13),],
    'tfn-aqwa-0m4a': [datetime.datetime(2018, 9,12),],
    'tfn-aqwa-0m4b': [datetime.datetime(2018, 9,12),],
}

# List of events when the telesocope mirro rwas changed.
# in practice, program will attempt to do a fit between dates listed here. so it does not matter what triggered
# the new slope calculation
mirrorreplacmenet = {
    'ogg-clma-2m0a': [datetime.datetime(2016,  4,1),
                      datetime.datetime(2017, 10,20),],

    'elp-doma-1m0a': [datetime.datetime(2016,  4,1),
                      datetime.datetime(2018, 4, 5), ],

    'coj-clma-2m0a': [datetime.datetime(2016,  4,1),
                      datetime.datetime(2018, 6, 20),],
    'coj-doma-1m0a': [datetime.datetime(2016, 10,1),
                      datetime.datetime(2018, 6, 18),] ,
    'coj-domb-1m0a': [datetime.datetime(2016, 10,1),
                      datetime.datetime(2018, 6, 10),] ,

    'lsc-doma-1m0a': [datetime.datetime(2016,  6,1),
                      datetime.datetime(2016, 10, 15),
                      datetime.datetime(2018, 9, 14),],
    'lsc-domb-1m0a': [datetime.datetime(2016,  4,1),
                      datetime.datetime(2018, 9, 14),],
    'lsc-domc-1m0a': [datetime.datetime(2016,  4,1),
                      datetime.datetime(2017, 8, 31),],

    'cpt-doma-1m0a': [datetime.datetime(2016, 10,1),
                      datetime.datetime(2016, 11, 1),
                      datetime.datetime(2018, 10, 24),],
    'cpt-domb-1m0a': [datetime.datetime(2016, 10,1),
                      datetime.datetime(2018, 10, 24),],
    'cpt-domc-1m0a': [datetime.datetime(2016, 10,1),
                      datetime.datetime(2018, 10, 24),],
}


telescopereferencethroughput = {'rp': {"1m0": 23.8, "2m0" : 25.35}}


def getCombineddataByTelescope(site, telescope, context, instrument=None, cacheddb=None):
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
        db=cacheddb
    _logger.debug ("Getting all photometry data for %s %s %s" % (site,telescope,instrument))
    dome, tel = telescope.split ("-")

    results =  db.readRecords(site,dome,tel,instrument)
    if cacheddb is None:
        db.close()
    return results

def dateformat (starttime,endtime):
    """ Utility to prettify a plot with dates.
    """

    plt.xlim([starttime, endtime])
    plt.gcf().autofmt_xdate()
    years = mdates.YearLocator()   # every year
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


def plotlongtermtrend(select_site, select_telescope, select_filter, context, instrument=None, cacheddb = None):

    data = getCombineddataByTelescope(select_site, select_telescope, context, instrument, cacheddb=cacheddb)

    mystarttime = starttime
    #if (select_site == 'elp') and (select_telescope=='doma-1m0a'):
    #    mystarttime = datetime.datetime(2014, 1, 1)

    if data is None:
        return
    # down-select data by viability and camera / filer combination
    selection = np.ones(len(data['name']), dtype=bool)

    if select_filter is not None:
        selection = selection & (data['filter'] == select_filter)
    if instrument is not None:
        selection = selection & (data['camera'] == instrument)

    # weed out bad data
    selection = selection & np.logical_not(np.isnan(data['zp']))
    selection = selection & np.logical_not(np.isnan(data['airmass']))

    if len(selection) == 0:
        _logger.warning ("No data points left after down selection. Not wasting time on empty plots.")
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
            photzpmaxnoise = 0.5

    # Calculate air-mass corrected photometric zeropoint; corrected to airmass of 1
    zp_air = zpselect + airmasscorrection[select_filter] * airmasselect - airmasscorrection[select_filter]

    # find the overall trend of zeropoint variations, save to output file.
    _x, _y = findUpperEnvelope(dateselect[zpsigselect < photzpmaxnoise], zp_air[zpsigselect < photzpmaxnoise],
                               ymax=ymax)

    if cacheddb is None:
        db = photdbinterface(context.database)
    else:
        db=cacheddb
    db.storemirrormodel("%s-%s" % (select_site,select_telescope), select_filter, _x,_y)

    if cacheddb is None:
        db.close()

    # now we are starting to plot stuff

    plt.figure()


    plot_referencethoughput(mystarttime, endtime, select_filter, select_telescope[-4:-1])
    # mark mirror cleaning events.
    for telid in telescopecleaning:
        _site,_enc,_tel = telid.split ("-")

        if (_site == select_site) and (select_telescope == '%s-%s' % (_enc,_tel)):
            for event in telescopecleaning[telid]:
                plt.axvline (x=event, color='grey', linestyle='--')

    #  plot all the zeropoint measurements, but label different cameras differently.
    uniquecameras = np.unique(cameraselect)

    for uc in uniquecameras:
        plt.plot(dateselect[(zpsigselect <= photzpmaxnoise) & (cameraselect == uc)],
                 zp_air[(zpsigselect <= photzpmaxnoise) & (cameraselect == uc)],
                 'o', markersize=2, label=uc)
        plt.plot(dateselect[zpsigselect > photzpmaxnoise], zp_air[zpsigselect > photzpmaxnoise], '.',
                 markersize=1, c="grey", label='_nolegend_' )

    if _x is not None:
        plt.plot(_x, _y, "-", c='red', label='upper envelope')

        for telid in mirrorreplacmenet:
            _site,_enc,_tel = telid.split ("-")
            if (_site == select_site) and (select_telescope == '%s-%s' % (_enc,_tel)):

                events =  mirrorreplacmenet[telid]
                events.append(datetime.datetime.utcnow())
                print (events)
                for ii in range (len(events)-1):
                    start = mirrorreplacmenet[telid][ii]
                    end = mirrorreplacmenet[telid][ii+1]
                    fittrendtomirrormodel(_x,_y, start, end, plot=True)

    else:
        _logger.warning("Mirror model failed to compute. not plotting !")

    # prettify, decorations, etc
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    plt.ylim([ymax - 3.5, ymax])
    dateformat(mystarttime,endtime)
    plt.xlabel("DATE-OBS")
    plt.ylabel("Photometric Zeropoint %s" % select_filter)
    plt.title("Long term throughput  %s:%s in %s" % (select_site, select_telescope, select_filter))

    # and finally safe the plot.
    outfigname = "%s/photzptrend-%s-%s-%s.png" % (
        context.imagedbPrefix, select_site, select_telescope, select_filter)
    plt.savefig(outfigname, bbox_inches="tight")
    plt.close()

    # for internal use: generate error plots.
    if context.errorhistogram:
        plt.figure()
        plt.hist(zpsigselect, 50, range=[0, 1], normed=True)
        outerrorhistfname = "%s/errorhist-%s-%s-%s.png" % (
            context.imagedbPrefix, select_site, select_telescope, select_filter)
        plt.savefig(outerrorhistfname)
        plt.close()

    # plot airmass vs zeropoint as a sanity check tool
    plt.figure()
    plt.plot(airmasselect, zpselect, ".", c="grey")
    plt.plot(airmasselect, zp_air, ".", c="blue")
    plt.xlabel("Airmass")
    plt.ylabel("Photomertic Zeropoint %s" % select_filter)
    plt.title ("Global airmass trend and correction check")
    meanzp = np.nanmedian(zpselect)
    plt.ylim([meanzp - 0.5, meanzp + 0.5])
    plt.savefig("%s/airmasstrend-%s-%s-%s.png" % (context.imagedbPrefix, select_site, select_telescope, select_filter))
    plt.close()

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
    plt.axhline(y=meancolorterm, color='r', linestyle='-')
    _logger.info("Color term in filter %s : % 5.3f" % (select_filter, meancolorterm))

    # store the color terms
    if select_filter not in colorterms:
        colorterms[select_filter] = {}
    colorterms[select_filter][instrument] = meancolorterm

    dateformat (mystarttime,endtime)
    plt.ylim([-0.2, 0.2])

    plt.title("Color term (g-r)  %s:%s in %s" % (select_site, select_telescope, select_filter))
    plt.xlabel("DATE-OBS")
    plt.ylabel("Color term coefficient (g-r)")
    plt.savefig(
        "%s/colortermtrend-%s-%s-%s.png" % (context.imagedbPrefix, select_site, select_telescope, select_filter))
    plt.close()

    # thats it, some day please refactor(select_filter, this into smaller chunks.


def plot_referencethoughput(start, end,select_filter, select_telescope):

    filterinreflux = select_filter in telescopereferencethroughput
    _logger.info ("filter %s  in referenceflux table %s" % (select_filter,filterinreflux))
    if not filterinreflux:
        return

    telescopeinreflux = select_telescope in telescopereferencethroughput[select_filter]
    _logger.info ("telescope %s in reference flux table: %s" % (select_telescope, telescopeinreflux))

    if filterinreflux and telescopeinreflux:

        goodvalue = telescopereferencethroughput[select_filter][select_telescope]
        rect = Rectangle((start, goodvalue), end - start, -0.2, color='#A0FFA0A0')
        plt.axes().add_patch(rect)


        # plt.axhline(telescopereferencethroughput[select_filter][select_telescope])


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


def fittrendtomirrormodel (dates,zps, start,end, order=1, plot=False):


    _logger.info ("Calculating trend line between %s and %s " % (start,end))

    poly = np.poly1d([0,0])

    try:
        select = (dates > start)
        select = select & (dates < end)
        _x = dates[select]
        _xx = mdates.date2num(_x)
        _y = zps[select]
        poly = np.poly1d(np.polyfit (_xx, _y, order))
        _logger.info("Slope calculated to % 5.3f mag / month" % (poly.c[0] * 30))

        if plot:

            _y = poly (_xx)
            plt.plot (_x,_y,"--", label="% 5.3f mag \nper month" % (poly.c[0] * 30))
    except:
        _logger.error ("While fitting phzp trend; probably not enough data points.")

    return poly

def plotallmirrormodels(context, type=['2m0a','1m0a'], range=[22.5,25.5], cacheddb = None):
    """ fetch mirror model from database for a selected class of telescopes and put them all into one single plot. """

    if cacheddb is None:
        db = photdbinterface(context.database)
    else:
        db=cacheddb

    myfilter = context.filter
    modellist = []

    for t in type:
        modellist.extend (db.findmirrormodels(t, myfilter))
        plot_referencethoughput(starttime, endtime, myfilter, t[0:3])

    modellist.sort(key = lambda x: x[0:3] + x[-1:-5].replace('2','0') + x[4:8])
    _logger.info ("Plotting several models in a single plot. These are the models returned from search %s: %s" % (type,modellist))

    plt.rc('lines', linewidth=1)
    prop_cycle=  cycle( ['-', '-.'])



    for model in modellist:
        _logger.debug ("Plotting mirror model %s" % model)
        data = db.readmirrormodel(model,myfilter)
        plt.gcf().autofmt_xdate()
        plt.plot(data['dateobs'], data['zp'],next(prop_cycle),  label=model.replace('-', ':'), )

    plt.legend(bbox_to_anchor=(1.01, 1), loc='upper left', ncol=1)
    plt.xlabel('DATE-OBS')
    plt.ylabel("phot zeropoint %s" % myfilter)
    dateformat (starttime,endtime)
    plt.ylim(range)
    plt.title("Photometric zeropoint model in filter %s" % myfilter)
    plt.grid(True, which='both')

    name=""
    for ii in type:
        name += str(ii)
    plt.savefig("%s/allmodels_%s_%s.png" % (context.imagedbPrefix, name, context.filter), bbox_inches='tight')
    plt.close()

    if cacheddb is None:
        db.close()


def renderHTMLPage (args):
    _logger.info ("Now rendering output html page")

    outputfile = "%s/index.html" % (args.imagedbPrefix)

    message = """<html>
<head></head>
<body><title>LCO Zeropoint Plots</title>
"""
    message += "<p/>Figures updated %s UTC <p/>\n"  % (datetime.datetime.utcnow())
    message += """
<h1> Overview </h1>
     <a href="allmodels_2m01m0_rp.png"> <img src="allmodels_2m01m0_rp.png"/ width="800"> </a>
     <a href="allmodels_0m4_rp.png"><img src="allmodels_0m4_rp.png" width="800"/></a>
    <p/>
    
<h1> Details by Site: </h1>
"""

    for site in telescopedict:
        message = message + " <h2> %s </h2>\n" % (site)

        zptrendimages = glob.glob ("%s/photzptrend-%s-????-????-rp.png" % (args.imagedbPrefix, site))

        zptrendimages.sort(key = lambda x: x[-16: -4])

        _logger.debug ("Found individual telescopes zp trend plots for site %s to include:\n\t %s " % (site,zptrendimages))

        for zptrend in zptrendimages:
            zptrend = zptrend.replace("%s/" % args.imagedbPrefix, "")
            line = '<a href="%s"><img src="%s" height="450"/></a>  <img src="%s" height="450"/>  <img src="%s" height="450"/><p/>' % (zptrend, zptrend, zptrend.replace('photzptrend', 'colortermtrend'), zptrend.replace('photzptrend', 'airmasstrend'))
            message = message + line

    message = message + "</body></html>"

    with open (outputfile, 'w+') as f:
        f.write (message)
        f.close()



def parseCommandLine():
    """ Read command line parameters
    """

    parser = argparse.ArgumentParser(
        description='Calculate long-term trends in photometric database.')

    parser.add_argument('--log_level', dest='log_level', default='INFO', choices=['DEBUG', 'INFO'],
                        help='Set the debug level')

    parser.add_argument('--outputdirectory', dest='imagedbPrefix', default='~/lcozpplots',
                        help='Directory containing photometryc databases')
    parser.add_argument('--database', default = '~/lcozpplots/lcophotzp.db')
    parser.add_argument('--site', dest='site', default=None, help='sites code for camera')
    parser.add_argument('--telescope', default=None,
                        help='Telescope id. written inform enclosure-telescope, e.g., "domb-1m0a"')
    parser.add_argument('--filter', default='rp', help='Which filter to process.', choices=['gp', 'rp', 'ip', 'zp'])
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


if __name__ == '__main__':
    plt.style.use('ggplot')
    matplotlib.rcParams['savefig.dpi'] = 400

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
                _logger.info ("Now plotting and fitting mirror model for %s %s in filter %s" % (site, telescope, args.filter))
                plotlongtermtrend(site, telescope, args.filter, args, cacheddb=db )

        db.close()

    # Generate mirror model plots for all telscopes in a single plot
    if args.createsummaryplots:
        plotallmirrormodels(args,type=['2m0','1m0'])
        plotallmirrormodels(args, type=['0m4'], range=[20,23])

    # Make a fancy HTML page
    if args.renderhtml:
        renderHTMLPage(args)

    sys.exit(0)

