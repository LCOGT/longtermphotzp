"""
Analyze the color term of the photometric relation per filter, per camera and per instrument group (all cameras of
one type on one telescope class at a site, e.g., lsc-1m0-fa), from the photometric zeropoint database.
Cameras of the kb, fl, and fs families are excluded by default.

photcalibration fits, per image,  refmag - instmag = zp + c * (g-i)_ref,  and stores the color term c with the
zeropoint. Here the per-image color terms are combined:

  * Atmospheric extinction is stronger for blue stars, so the color term can change with airmass (second-order
    extinction). Per camera and filter, c = c(X=1) + dc/dX * (X - 1) is fitted to the sigma-clipped per-image color
    terms, with every night given the same total weight so that nights with many exposures do not dominate.
    The reported color term is the value extrapolated to airmass 1, c(X=1). Uncertainties are bootstrapped over nights.
  * The mean over nights of the nightly mean color term (at the airmasses observed) is reported for comparison, and
    the scatter of the per-image color terms around the fit as a measure of the per-image precision.
"""

import argparse
import datetime
import logging
import os

import matplotlib

matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
from astropy.table import Table

from longtermphotzp.airmassterms import (EXCLUDED_CAMERA_PREFIXES, _to_datetime64, _to_float, camera_type_filter,
                                         instrument_groups, night_keys, _style, COLOR_DATA, COLOR_FIT, COLOR_TEXT)
from longtermphotzp.logging_config import setup_logging
from longtermphotzp.photdbinterface import photdbinterface, PhotZPMeasurement

_logger = logging.getLogger(__name__)

# Filters with a color term fit in photcalibration (the reference color is always (g-i) from the reference catalog).
DEFAULT_FILTERS = ['up', 'gp', 'rp', 'ip', 'zp', 'zs', 'Y', 'U', 'B', 'V', 'R', 'Rc', 'I']


def read_colorterms(dburl, filters, cameras=None, sites=None, start=None, end=None, cameratypes=None):
    """ Read the columns needed for the color term analysis from the zeropoint database.

    :param cameratypes: select all cameras of these types (name prefixes), e.g., ['ep', 'fa', 'sq'].

    :return: dict of numpy arrays (dateobs, site, telescope, camera, filter, airmass, colorterm, zpsig), or None if
             nothing matched.
    """
    db = photdbinterface(dburl)
    M = PhotZPMeasurement
    q = db.session.query(M.dateobs, M.site, M.telescope, M.camera, M.filter, M.airmass, M.colorterm, M.zpsig).filter(
        M.filter.in_(filters))
    if cameras:
        q = q.filter(M.camera.in_(cameras))
    if cameratypes:
        q = q.filter(camera_type_filter(M.camera, cameratypes))
    if sites:
        q = q.filter(M.site.in_(sites))
    # DATE-OBS is stored as an ISO-like string, so lexical comparison works for date limits.
    if start:
        q = q.filter(M.dateobs >= start)
    if end:
        q = q.filter(M.dateobs < end)
    rows = q.all()
    db.close()

    _logger.info(f"Read {len(rows)} zeropoint records from database")
    if len(rows) == 0:
        return None

    dateobs, site, telescope, camera, filt, airmass, colorterm, zpsig = zip(*rows)
    return {
        'dateobs': _to_datetime64(dateobs),
        'site': np.array(site, dtype=str),
        'telescope': np.array(telescope, dtype=str),
        'camera': np.array(camera, dtype=str),
        'filter': np.array(filt, dtype=str),
        'airmass': _to_float(airmass),
        'colorterm': _to_float(colorterm),
        'zpsig': _to_float(zpsig),
    }


def _night_sums(colorterm, airmass, inv, use, nnights):
    """ Per-night weighted sums for the linear fit c = c1 + dcdx * (X - 1); each night carries a total weight of 1. """
    n = np.bincount(inv, weights=use, minlength=nnights)
    w = use / np.maximum(n, 1)[inv]
    dX = airmass - 1.
    return [np.bincount(inv, weights=w * v, minlength=nnights)
            for v in (np.ones_like(dX), dX, dX * dX, colorterm, dX * colorterm)]


def _solve(s1, sx, sxx, sy, sxy):
    """ Weighted least squares line from summed moments; returns (value at airmass 1, slope). """
    det = s1 * sxx - sx * sx
    with np.errstate(divide='ignore', invalid='ignore'):
        slope = (s1 * sxy - sx * sy) / det
        c1 = (sy - slope * sx) / s1
    return c1, slope


def fit_colorterm(colorterm, airmass, nightkey, min_points_per_night=1, clip_sigma=3., maxiter=20):
    """ Fit c = c(X=1) + dc/dX * (X - 1) to the per-image color terms, with equal total weight per night and iterative
    sigma clipping around the fitted line. If the airmass range is too small to constrain a slope, the slope is set to
    zero and c(X=1) is the night-averaged mean.

    :return: dict with the color term at airmass 1, the airmass dependence, the night-averaged mean color term, the
             per-image scatter, and per-point / per-night diagnostics, or None if no night qualifies.
    """
    nights, inv = np.unique(nightkey, return_inverse=True)
    nnights = len(nights)
    good = np.ones(len(colorterm), dtype=bool)

    for iteration in range(maxiter):
        n = np.bincount(inv, weights=good, minlength=nnights)
        nightok = n >= min_points_per_night
        use = good & nightok[inv]
        if use.sum() == 0:
            return None
        sums = [s[nightok].sum() for s in _night_sums(colorterm, airmass, inv, use, nnights)]
        c1, dcdx = _solve(*sums)
        if not (np.isfinite(c1) and np.isfinite(dcdx)) or np.ptp(airmass[use]) < 0.1:
            dcdx = 0.
            c1 = sums[3] / sums[0]
        resid = colorterm - (c1 + dcdx * (airmass - 1.))
        sigma = 1.4826 * np.median(np.abs(resid[use]))
        newgood = np.abs(resid) < clip_sigma * max(sigma, 1e-3)
        if np.array_equal(newgood, good):
            break
        good = newgood

    usednights = np.nonzero(nightok)[0]
    nightmean = np.bincount(inv, weights=colorterm * use, minlength=nnights) / np.maximum(
        np.bincount(inv, weights=use, minlength=nnights), 1)
    return {
        'c': c1, 'dcdx': dcdx,
        'c_mean': np.mean(nightmean[usednights]),
        'scatter': np.std(resid[use]),
        'npoints': int(use.sum()), 'nnights': len(usednights),
        'use': use, 'inv': inv, 'nightmean': nightmean, 'usednights': usednights,
    }


def bootstrap_colorterm(fit, colorterm, airmass, nboot=500, rng=None):
    """ Bootstrap the color term at airmass 1 and its airmass dependence by resampling nights.

    :return: (error of the color term at airmass 1, error of the airmass slope)
    """
    rng = np.random.default_rng(rng)
    use, inv, usednights = fit['use'], fit['inv'], fit['usednights']
    draws = rng.integers(0, len(usednights), size=(nboot, len(usednights)))
    sums = [s[usednights][draws].sum(axis=1) for s in _night_sums(colorterm, airmass, inv, use, inv.max() + 1)]
    c1, slopes = _solve(*sums)
    if fit['dcdx'] == 0.:
        # no airmass leverage: the color term is the night-averaged mean
        c1, slopes = sums[3] / sums[0], np.zeros(nboot)
    ok = np.isfinite(c1) & np.isfinite(slopes)
    if ok.sum() < 2:
        return np.nan, np.nan
    return np.std(c1[ok]), np.std(slopes[ok])


def plot_group(fit, colorterm, airmass, dateobs, label, filt, cerr, dcdxerr, outdir):
    """ Three-panel diagnostic: color term at airmass 1 vs time, color term vs airmass, and the distribution of the
    color terms at airmass 1. """
    use = fit['use']
    c = fit['c']
    # per-image color terms corrected to airmass 1 with the fitted airmass dependence
    c1 = colorterm - fit['dcdx'] * (airmass - 1.)
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 4.5), gridspec_kw={'width_ratios': [3, 2, 2]})

    dates = dateobs.astype('datetime64[ms]').astype(datetime.datetime)
    ax1.plot(dates[use], c1[use], '.', ms=3, color=COLOR_DATA, alpha=0.5, rasterized=True)
    ax1.plot(dates[~use], c1[~use], 'x', ms=3, color=COLOR_DATA, alpha=0.3, rasterized=True)
    # nightly means at the mean time of each night
    inv = fit['inv']
    tnum = mdates.date2num(dates)
    nn = np.bincount(inv, weights=use, minlength=inv.max() + 1)
    tmean = np.bincount(inv, weights=tnum * use, minlength=inv.max() + 1) / np.maximum(nn, 1)
    nights = fit['usednights']
    c1night = np.bincount(inv, weights=c1 * use, minlength=inv.max() + 1) / np.maximum(nn, 1)
    ax1.plot(mdates.num2date(tmean[nights]), c1night[nights], 'o', ms=6, color=COLOR_FIT,
             markeredgecolor='white', markeredgewidth=1, label='nightly mean', zorder=4)
    ax1.axhspan(c - cerr, c + cerr, color=COLOR_FIT, alpha=0.2, lw=0)
    ax1.axhline(c, color=COLOR_FIT, lw=2, label=f'c(X=1) = {c:+.3f} ± {cerr:.3f}')
    ax1.set_ylabel('Color term at airmass 1 [mag / mag (g-i)]')
    ax1.legend(loc='upper right', frameon=False)
    locator = mdates.AutoDateLocator()
    ax1.xaxis.set_major_locator(locator)
    ax1.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))

    ax2.plot(airmass[use], colorterm[use], '.', ms=3, color=COLOR_DATA, alpha=0.5, rasterized=True)
    xp = np.array([1., max(2., np.nanmax(airmass[use]))])
    ax2.plot(xp, c + fit['dcdx'] * (xp - 1), '-', lw=2, color=COLOR_FIT,
             label=f'dc/dX = {fit["dcdx"]:+.3f} ± {dcdxerr:.3f}')
    ax2.set_xlabel('Airmass')
    ax2.set_ylabel('Color term [mag / mag (g-i)]')
    ax2.legend(loc='upper right', frameon=False)

    lo, hi = np.percentile(np.r_[colorterm[use], c1[use]], [1, 99])
    pad = 0.5 * (hi - lo) + 0.01
    ax3.hist(c1[use], bins=30, range=(lo - pad, hi + pad), color=COLOR_DATA, edgecolor='white', linewidth=1)
    ax3.axvline(c, color=COLOR_FIT, lw=2)
    ax3.set_xlabel('Color term at airmass 1 [mag / mag (g-i)]')
    ax3.set_ylabel('Images')
    ax3.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax3.set_title(f'per-image scatter {fit["scatter"]:.3f}', fontsize=10, color=COLOR_TEXT)

    for ax in (ax1, ax2):
        ax.set_ylim(lo - pad, hi + pad)
    fig.suptitle(f'Color term {label} in {filt}:  {fit["npoints"]} images, {fit["nnights"]} nights')
    _style(fig)
    filename = os.path.join(outdir, f'colorterm-{label}-{filt}.png')
    fig.savefig(filename, bbox_inches='tight', dpi=120)
    plt.close(fig)
    return filename


def plot_summary(results, groupcolumn, outdir):
    """ Small multiples, one panel per filter: color term per camera or instrument group. """
    filters = [f for f in DEFAULT_FILTERS if f in set(results['filter'])]
    if len(filters) == 0:
        return None
    ncols = min(3, len(filters))
    nrows = int(np.ceil(len(filters) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 3.6 * nrows), squeeze=False)

    for ax, filt in zip(axes.flat, filters):
        r = results[results['filter'] == filt]
        r.sort(groupcolumn)
        x = np.arange(len(r))
        ax.errorbar(x, r['c'], yerr=r['c_err'], fmt='o', ms=6, color=COLOR_FIT, ecolor=COLOR_FIT, elinewidth=1.5,
                    capsize=0)
        ax.axhline(0, color=COLOR_TEXT, lw=0.8)
        ax.set_xticks(x)
        labels = [f'{g} ({s})' for g, s in zip(r[groupcolumn], r['sites'])] if groupcolumn == 'camera' \
            else r[groupcolumn]
        ax.set_xticklabels(labels, rotation=60, ha='right', fontsize=8)
        ax.set_title(filt)
        ax.set_ylabel('c(X=1) [mag / mag (g-i)]')
    for ax in list(axes.flat)[len(filters):]:
        ax.set_visible(False)

    grouplabel = 'camera' if groupcolumn == 'camera' else 'site / telescope class / camera type'
    fig.suptitle(f'Color terms at airmass 1 per {grouplabel}')
    fig.tight_layout()
    _style(fig)
    filename = os.path.join(outdir, f'colorterms-summary-{groupcolumn}.png')
    fig.savefig(filename, bbox_inches='tight', dpi=120)
    plt.close(fig)
    return filename


def analyze(data, groupcolumn, args, outdir):
    """ Determine the color term for every (group, filter) combination, where group is 'camera' or 'instrumentgroup'. """
    rows = []
    for filt in [f for f in args.filters if f in set(data['filter'])]:
        for group in sorted(set(data[groupcolumn][data['filter'] == filt])):
            sel = (data['filter'] == filt) & (data[groupcolumn] == group)
            nimages = int(sel.sum())
            fit = fit_colorterm(data['colorterm'][sel], data['airmass'][sel], data['night'][sel],
                                min_points_per_night=args.min_points_per_night)
            if fit is None or fit['nnights'] < args.min_nights:
                _logger.info(f"{group} {filt}: not enough usable nights ({0 if fit is None else fit['nnights']}), "
                             f"skipping")
                continue

            cerr, dcdxerr = bootstrap_colorterm(fit, data['colorterm'][sel], data['airmass'][sel],
                                                nboot=args.nbootstrap, rng=42)
            rows.append({
                groupcolumn: group, 'filter': filt,
                'sites': ','.join(sorted(set(data['site'][sel]))),
                'nimages': nimages, 'nused': fit['npoints'], 'nnights': fit['nnights'],
                'c': fit['c'], 'c_err': cerr, 'dc_dX': fit['dcdx'], 'dc_dX_err': dcdxerr,
                'c_mean': fit['c_mean'], 'scatter': fit['scatter'],
            })
            _logger.info(f"{group:6s} {filt:3s}: c(X=1) = {fit['c']:+.3f} ± {cerr:.3f}, scatter {fit['scatter']:.3f}, "
                         f"dc/dX = {fit['dcdx']:+.3f} ± {dcdxerr:.3f}, {fit['nnights']} nights, {fit['npoints']} images")
            if args.plots:
                plot_group(fit, data['colorterm'][sel], data['airmass'][sel], data['dateobs'][sel], group, filt,
                           cerr, dcdxerr, outdir)

    if len(rows) == 0:
        return None
    results = Table(rows=rows)
    for col in ['c', 'c_err', 'dc_dX', 'dc_dX_err', 'c_mean', 'scatter']:
        results[col].info.format = '.3f'
    return results


def parseCommandLine():
    parser = argparse.ArgumentParser(
        description='Determine the color term of the photometric relation per filter, per camera and per site / '
                    'telescope class / camera type, from the photometric zeropoint database.')
    parser.add_argument('--database', default=os.environ.get('DATABASE', 'sqlite:///lcophotzp.db'),
                        help='SQLAlchemy database URL. Default: $DATABASE or sqlite:///lcophotzp.db')
    parser.add_argument('--outputdirectory', default='./colorterms', help='Directory for plots and tables')
    parser.add_argument('--filters', nargs='+', default=DEFAULT_FILTERS)
    parser.add_argument('--cameras', nargs='+', default=None, help='Restrict to these cameras')
    parser.add_argument('--camera-types', dest='cameratypes', nargs='+', default=None,
                        help='Restrict to all cameras of these types, e.g., ep fa sq')
    parser.add_argument('--sites', nargs='+', default=None, help='Restrict to these sites')
    parser.add_argument('--exclude-camera-prefixes', nargs='*', default=EXCLUDED_CAMERA_PREFIXES,
                        help=f'Skip cameras whose name starts with these prefixes. Default: {EXCLUDED_CAMERA_PREFIXES}')
    parser.add_argument('--start', default=None, help='Earliest DATE-OBS, e.g., 2022-01-01')
    parser.add_argument('--end', default=None, help='Latest DATE-OBS (exclusive)')
    parser.add_argument('--maxzpsig', type=float, default=0.1,
                        help='Reject images with a per-image zeropoint scatter above this [mag]')
    parser.add_argument('--maxcolorterm', type=float, default=0.5,
                        help='Reject per-image color terms with an absolute value above this (failed fits)')
    parser.add_argument('--min-points-per-night', type=int, default=1)
    parser.add_argument('--min-nights', type=int, default=3, help='Minimum usable nights to report a result')
    parser.add_argument('--nbootstrap', type=int, default=500)
    parser.add_argument('--no-plots', dest='plots', action='store_false', help='Only produce the summary tables')
    parser.add_argument('--log-level', dest='log_level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING'])
    args = parser.parse_args()
    setup_logging(level=args.log_level)
    args.outputdirectory = os.path.expanduser(args.outputdirectory)
    return args


def main():
    args = parseCommandLine()
    os.makedirs(args.outputdirectory, exist_ok=True)

    data = read_colorterms(args.database, args.filters, cameras=args.cameras, sites=args.sites, start=args.start,
                           end=args.end, cameratypes=args.cameratypes)
    if data is None:
        _logger.error("No zeropoint records found for the selection.")
        return 1

    valid = (np.isfinite(data['colorterm']) & (np.abs(data['colorterm']) < args.maxcolorterm) &
             np.isfinite(data['airmass']) & (data['airmass'] >= 1.) & (data['airmass'] < 3.) &
             np.isfinite(data['zpsig']) & (data['zpsig'] < args.maxzpsig) & ~np.isnat(data['dateobs']))
    for prefix in args.exclude_camera_prefixes:
        valid &= ~np.char.startswith(data['camera'], prefix)
    _logger.info(f"{valid.sum()} of {len(valid)} records pass basic quality cuts")
    data = {key: value[valid] for key, value in data.items()}
    data['night'] = np.char.add(np.char.add(night_keys(data['dateobs'], data['site']), ':'), data['camera'])
    data['instrumentgroup'] = instrument_groups(data['site'], data['telescope'], data['camera'])

    for groupcolumn in ('camera', 'instrumentgroup'):
        results = analyze(data, groupcolumn, args, args.outputdirectory)
        if results is None:
            _logger.warning(f"No {groupcolumn} / filter combination had enough data for a fit.")
            continue
        basename = os.path.join(args.outputdirectory, f'colorterms-{groupcolumn}')
        results.meta['created'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        results.meta['database'] = args.database.split('@')[-1]
        results.write(f'{basename}.ecsv', overwrite=True)
        results.write(f'{basename}.csv', overwrite=True)
        if args.plots:
            plot_summary(results, groupcolumn, args.outputdirectory)
        print(f"\nColor terms at airmass 1 (c) per {groupcolumn} and filter [mag / mag (g-i)]:")
        results.pprint_all()

    return 0


if __name__ == '__main__':
    main()
