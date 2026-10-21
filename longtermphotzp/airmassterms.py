"""
Empirically determine the atmospheric extinction (airmass) term per filter from the photometric zeropoint database,
both per camera and per instrument group: all cameras of one type on one telescope class at a site (e.g., lsc-1m0-fa).
Cameras of the kb, fl, and fs families are excluded by default.

Method:
  Within a single night, the telescope throughput and (on a photometric night) the transparency are constant, so
  the zeropoints of a night only vary with airmass as  zp = zp_night - k * X.  We therefore fit a single extinction
  coefficient k with a free zeropoint per night (a "fixed effects" fit: subtract each night's mean zeropoint and mean
  airmass, then fit a line through the origin). This removes the long-term mirror degradation and night-to-night
  transparency changes. Points are sigma-clipped, and nights with a large residual scatter (non-photometric) or a
  small airmass range (no leverage) are rejected. Uncertainties are bootstrapped over nights.

  The sign convention matches photzptrends.airmasscorrection: zp_corrected = zp + k * (X - 1).
"""

import argparse
import datetime
import logging
import os

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
from astropy.table import Table
from sqlalchemy import or_

from longtermphotzp.logging_config import setup_logging
from longtermphotzp.photdbinterface import photdbinterface, PhotZPMeasurement
from longtermphotzp.photzptrends import airmasscorrection

_logger = logging.getLogger(__name__)

# Geographic longitude [deg, east positive] of LCO sites; used to group exposures into local nights.
SITE_LONGITUDE = {
    'lsc': -70.80, 'cpt': 20.81, 'ogg': -156.26, 'coj': 149.07, 'tfn': -16.51, 'elp': -104.02,
    'tlv': 34.76, 'sqa': -120.04, 'bpl': -119.86,
}

# Camera families that are not analyzed by default.
EXCLUDED_CAMERA_PREFIXES = ['kb', 'fl', 'fs']

COLOR_FIT = '#2a78d6'
COLOR_HARDCODED = '#eb6834'
COLOR_DATA = '#8a8984'
COLOR_TEXT = '#52514e'


def _to_float(values):
    """ Convert database values to float; non-numeric entries such as 'UNKNOWN' become nan. """
    out = np.full(len(values), np.nan)
    for ii, v in enumerate(values):
        try:
            out[ii] = float(v)
        except (TypeError, ValueError):
            pass
    return out


def _to_datetime64(values):
    """ Parse DATE-OBS strings ('2020-01-13 05:12:33.123' or ISO 'T' form); unparseable entries become NaT. """
    strings = [str(v).strip().replace(' ', 'T') for v in values]
    try:
        return np.array(strings, dtype='datetime64[ms]')
    except ValueError:
        out = np.full(len(strings), np.datetime64('NaT'), dtype='datetime64[ms]')
        for ii, s in enumerate(strings):
            try:
                out[ii] = np.datetime64(s, 'ms')
            except ValueError:
                pass
        return out


def camera_type_filter(column, cameratypes):
    """ SQL condition selecting all cameras whose name starts with one of the camera types, e.g., ['ep', 'sq']. """
    return or_(*[column.like(f'{t}%') for t in cameratypes])


def read_zeropoints(dburl, filters, cameras=None, sites=None, start=None, end=None, cameratypes=None):
    """ Read the columns needed for the airmass analysis from the zeropoint database.

    :param cameratypes: select all cameras of these types (name prefixes), e.g., ['ep', 'fa', 'sq'].

    :return: dict of numpy arrays (dateobs, site, camera, filter, airmass, zp, zpsig), or None if nothing matched.
    """
    db = photdbinterface(dburl)
    M = PhotZPMeasurement
    q = db.session.query(M.dateobs, M.site, M.telescope, M.camera, M.filter, M.airmass, M.zp, M.zpsig).filter(
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

    dateobs, site, telescope, camera, filt, airmass, zp, zpsig = zip(*rows)
    return {
        'dateobs': _to_datetime64(dateobs),
        'site': np.array(site, dtype=str),
        'telescope': np.array(telescope, dtype=str),
        'camera': np.array(camera, dtype=str),
        'filter': np.array(filt, dtype=str),
        'airmass': _to_float(airmass),
        'zp': _to_float(zp),
        'zpsig': _to_float(zpsig),
    }


def instrument_groups(site, telescope, camera):
    """ Label each exposure as site-telescopeclass-cameratype, e.g., 'lsc-1m0-fa' for all fa cameras on lsc 1m0s. """
    telclass = np.array([t[:3] if len(t) >= 3 and t[1] == 'm' else 'unknown' for t in telescope])
    camtype = np.array([c[:2] for c in camera])
    return np.char.add(np.char.add(np.char.add(np.char.add(site, '-'), telclass), '-'), camtype)


def night_keys(dateobs, site):
    """ Label each exposure with its site and local night (the calendar date at the start of the night). """
    lon = np.array([SITE_LONGITUDE.get(s, np.nan) for s in site])
    unknown = sorted(set(site[~np.isfinite(lon)]))
    if unknown:
        _logger.warning(f"Unknown site longitude for {unknown}, grouping nights by UTC date")
        lon[~np.isfinite(lon)] = 0.
    # local solar time, shifted by 12 h so that a whole night falls onto a single date.
    offset = np.round(lon / 15. * 3600e3).astype(np.int64).astype('timedelta64[ms]')
    nightdate = (dateobs + offset - np.timedelta64(12, 'h')).astype('datetime64[D]')
    return np.char.add(np.char.add(site, ':'), nightdate.astype(str))


def fit_airmass_term(airmass, zp, nightkey, min_points_per_night=5, min_airmass_span=0.2, max_night_rms=0.05,
                     clip_sigma=3., maxiter=20):
    """ Fit zp = zp_night - k * airmass with one free zeropoint per night and a common extinction coefficient k.

    :return: dict with the fit result and per-point / per-night diagnostics, or None if no night qualifies.
    """
    nights, inv = np.unique(nightkey, return_inverse=True)
    nnights = len(nights)
    good = np.ones(len(zp), dtype=bool)
    nightrms = np.zeros(nnights)
    use = None

    for iteration in range(maxiter):
        count = np.bincount(inv, weights=good, minlength=nnights)
        xmin = np.full(nnights, np.inf)
        xmax = np.full(nnights, -np.inf)
        np.minimum.at(xmin, inv[good], airmass[good])
        np.maximum.at(xmax, inv[good], airmass[good])
        nightok = (count >= min_points_per_night) & ((xmax - xmin) >= min_airmass_span) & (nightrms <= max_night_rms)

        newuse = good & nightok[inv]
        if use is not None and np.array_equal(newuse, use):
            break
        use = newuse
        if use.sum() == 0:
            return None

        n = np.bincount(inv, weights=use, minlength=nnights)
        nsafe = np.maximum(n, 1)
        meanx = np.bincount(inv, weights=airmass * use, minlength=nnights) / nsafe
        meanzp = np.bincount(inv, weights=zp * use, minlength=nnights) / nsafe
        dx = airmass - meanx[inv]
        dz = zp - meanzp[inv]
        sxx = np.sum((dx * dx)[use])
        if sxx <= 0:
            return None
        slope = np.sum((dx * dz)[use]) / sxx

        resid = dz - slope * dx
        sigma = 1.4826 * np.median(np.abs(resid[use]))
        good = np.abs(resid) < clip_sigma * max(sigma, 1e-3)
        nightrms = np.sqrt(np.bincount(inv, weights=resid ** 2 * use, minlength=nnights) / nsafe)

    usednights = np.unique(inv[use])
    return {
        'k': -slope,
        'k_err_formal': np.std(resid[use]) / np.sqrt(sxx),
        'residual_rms': np.std(resid[use]),
        'npoints': int(use.sum()),
        'nnights': len(usednights),
        'use': use, 'inv': inv, 'dx': dx, 'dz': dz, 'usednights': usednights,
    }


def bootstrap_k(fit, nboot=500, rng=None):
    """ Bootstrap the extinction coefficient by resampling nights (keeps within-night correlations intact). """
    rng = np.random.default_rng(rng)
    use, inv, dx, dz = fit['use'], fit['inv'], fit['dx'], fit['dz']
    nnights = inv.max() + 1
    sxy = np.bincount(inv, weights=(dx * dz) * use, minlength=nnights)[fit['usednights']]
    sxx = np.bincount(inv, weights=(dx * dx) * use, minlength=nnights)[fit['usednights']]
    draws = rng.integers(0, len(sxx), size=(nboot, len(sxx)))
    return np.std(-sxy[draws].sum(axis=1) / sxx[draws].sum(axis=1))


def per_night_k(fit, min_span=0.3):
    """ Extinction coefficient fitted to each well-sampled night individually, for diagnostics. """
    use, inv, dx, dz = fit['use'], fit['inv'], fit['dx'], fit['dz']
    nnights = inv.max() + 1
    sxy = np.bincount(inv, weights=(dx * dz) * use, minlength=nnights)
    sxx = np.bincount(inv, weights=(dx * dx) * use, minlength=nnights)
    xmin = np.full(nnights, np.inf)
    xmax = np.full(nnights, -np.inf)
    np.minimum.at(xmin, inv[use], (dx)[use])
    np.maximum.at(xmax, inv[use], (dx)[use])
    sel = (xmax - xmin) >= min_span
    return -sxy[sel] / sxx[sel]


def plot_group(fit, knights, airmass, label, filt, kerr, outdir):
    """ Two-panel diagnostic: zeropoint vs absolute airmass, and the distribution of per-night terms.

    Each zeropoint is shown relative to its night's fitted zeropoint at airmass 1 (the reference the pipeline corrects
    to), which removes night-to-night throughput and transparency offsets while keeping airmass on an absolute scale.
    """
    use, dx, dz = fit['use'], fit['dx'], fit['dz']
    k = fit['k']
    khard = airmasscorrection.get(filt)
    # night mean airmass is airmass - dx; shift the night-demeaned zeropoint to the night's model value at X = 1.
    rel = dz + k * (1. - (airmass - dx))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={'width_ratios': [3, 2]})

    ax1.plot(airmass[use], rel[use], '.', ms=2, color=COLOR_DATA, alpha=0.4, label='_nolegend_', rasterized=True)
    ax1.plot(airmass[~use], rel[~use], '.', ms=1, color=COLOR_DATA, alpha=0.1, label='_nolegend_', rasterized=True)
    bins = np.linspace(1., 3., 21)
    centers, medians = [], []
    for lo, hi in zip(bins[:-1], bins[1:]):
        sel = use & (airmass >= lo) & (airmass < hi)
        if sel.sum() >= 10:
            centers.append(0.5 * (lo + hi))
            medians.append(np.median(rel[sel]))
    ax1.plot(centers, medians, 'o', ms=6, color=COLOR_FIT, markeredgecolor='white', markeredgewidth=1,
             label='binned median', zorder=4)
    xp = np.array([0., 3.])
    ax1.plot(xp, -k * (xp - 1), '-', lw=2, color=COLOR_FIT, label=f'fit  k = {k:.3f} ± {kerr:.3f}', zorder=3)
    if khard is not None:
        ax1.plot(xp, -khard * (xp - 1), '--', lw=2, color=COLOR_HARDCODED, label=f'hard-coded  k = {khard:.3f}',
                 zorder=3)
    ax1.axvline(1., color=COLOR_TEXT, lw=0.8, ls=':', zorder=1)
    ax1.set_xlim(0, 3)
    kmax = max(abs(k), abs(khard or k))
    margin = 4 * fit['residual_rms']
    ax1.set_ylim(-2 * kmax - margin, kmax + margin)
    ax1.set_xlabel('Airmass')
    ax1.set_ylabel('Zeropoint − nightly zeropoint at airmass 1 [mag]')
    ax1.legend(loc='upper right', frameon=False)

    if len(knights) > 0:
        lo, hi = np.percentile(knights, [2, 98])
        lo, hi = min(lo, k, khard or k) - 0.02, max(hi, k, khard or k) + 0.02
        ax2.hist(knights, bins=30, range=(lo, hi), color=COLOR_DATA, edgecolor='white', linewidth=1)
        ax2.axvline(k, color=COLOR_FIT, lw=2, label='joint fit')
        if khard is not None:
            ax2.axvline(khard, color=COLOR_HARDCODED, lw=2, ls='--', label='hard-coded')
        ax2.set_xlim(lo, hi)
        ax2.legend(loc='upper right', frameon=False)
    ax2.set_xlabel('Per-night airmass term k [mag / airmass]')
    ax2.set_ylabel('Nights')
    ax2.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax2.set_title(f'{len(knights)} nights with airmass span ≥ 0.3', fontsize=10, color=COLOR_TEXT)

    fig.suptitle(f'Airmass term {label} in {filt}:  {fit["npoints"]} images, {fit["nnights"]} nights')
    _style(fig)
    filename = os.path.join(outdir, f'airmassterm-{label}-{filt}.png')
    fig.savefig(filename, bbox_inches='tight', dpi=120)
    plt.close(fig)
    return filename


def plot_summary(results, groupcolumn, outdir):
    """ Small multiples, one panel per filter: fitted airmass term per camera or instrument group vs the hard-coded value. """
    filters = [f for f in airmasscorrection if f in set(results['filter'])]
    if len(filters) == 0:
        return None
    ncols = min(3, len(filters))
    nrows = int(np.ceil(len(filters) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 3.6 * nrows), squeeze=False)

    for ax, filt in zip(axes.flat, filters):
        r = results[results['filter'] == filt]
        r.sort(groupcolumn)
        x = np.arange(len(r))
        ax.errorbar(x, r['k'], yerr=r['k_err'], fmt='o', ms=6, color=COLOR_FIT, ecolor=COLOR_FIT, elinewidth=1.5,
                    capsize=0, label='fit')
        ax.axhline(airmasscorrection[filt], color=COLOR_HARDCODED, ls='--', lw=2, label='hard-coded')
        ax.set_xticks(x)
        labels = [f'{g} ({s})' for g, s in zip(r[groupcolumn], r['sites'])] if groupcolumn == 'camera' \
            else r[groupcolumn]
        ax.set_xticklabels(labels, rotation=60, ha='right', fontsize=8)
        ax.set_title(filt)
        ax.set_ylabel('k [mag / airmass]')
    for ax in list(axes.flat)[len(filters):]:
        ax.set_visible(False)
    axes.flat[0].legend(loc='best', frameon=False)

    grouplabel = 'camera' if groupcolumn == 'camera' else 'site / telescope class / camera type'
    fig.suptitle(f'Fitted airmass terms per {grouplabel}')
    fig.tight_layout()
    _style(fig)
    filename = os.path.join(outdir, f'airmassterms-summary-{groupcolumn}.png')
    fig.savefig(filename, bbox_inches='tight', dpi=120)
    plt.close(fig)
    return filename


def _style(fig):
    for ax in fig.axes:
        ax.grid(True, color='#e4e3df', lw=0.8)
        ax.set_axisbelow(True)
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)


def analyze(data, groupcolumn, args, outdir):
    """ Fit the airmass term for every (group, filter) combination, where group is 'camera' or 'instrumentgroup'
    (all cameras of one type on one telescope class at a site, e.g., 'lsc-1m0-fa'). """
    rows = []
    for filt in [f for f in args.filters if f in set(data['filter'])]:
        for group in sorted(set(data[groupcolumn][data['filter'] == filt])):
            sel = (data['filter'] == filt) & (data[groupcolumn] == group)
            nimages = int(sel.sum())
            fit = fit_airmass_term(data['airmass'][sel], data['zp'][sel], data['night'][sel],
                                   min_points_per_night=args.min_points_per_night,
                                   min_airmass_span=args.min_airmass_span, max_night_rms=args.max_night_rms)
            if fit is None or fit['nnights'] < args.min_nights:
                _logger.info(f"{group} {filt}: not enough usable nights ({0 if fit is None else fit['nnights']}), "
                             f"skipping")
                continue

            kerr = bootstrap_k(fit, nboot=args.nbootstrap, rng=42)
            knights = per_night_k(fit)
            khard = airmasscorrection.get(filt, np.nan)
            rows.append({
                groupcolumn: group, 'filter': filt,
                'sites': ','.join(sorted(set(data['site'][sel]))),
                'nimages': nimages, 'nused': fit['npoints'], 'nnights': fit['nnights'],
                'k': fit['k'], 'k_err': kerr, 'k_err_formal': fit['k_err_formal'],
                'k_pernight_median': np.median(knights) if len(knights) else np.nan,
                'k_hardcoded': khard, 'k_minus_hardcoded': fit['k'] - khard,
                'residual_rms': fit['residual_rms'],
            })
            _logger.info(f"{group:6s} {filt:3s}: k = {fit['k']:.3f} ± {kerr:.3f} (hard-coded {khard:.3f}), "
                         f"{fit['nnights']} nights, {fit['npoints']} images")
            if args.plots:
                plot_group(fit, knights, data['airmass'][sel], group, filt, kerr, outdir)

    if len(rows) == 0:
        return None
    results = Table(rows=rows)
    for col in ['k', 'k_err', 'k_err_formal', 'k_pernight_median', 'k_hardcoded', 'k_minus_hardcoded',
                'residual_rms']:
        results[col].info.format = '.3f'
    return results


def parseCommandLine():
    parser = argparse.ArgumentParser(
        description='Determine atmospheric extinction (airmass) terms per filter, per camera and per site / telescope '
                    'class / camera type, from the photometric zeropoint database.')
    parser.add_argument('--database', default=os.environ.get('DATABASE', 'sqlite:///lcophotzp.db'),
                        help='SQLAlchemy database URL. Default: $DATABASE or sqlite:///lcophotzp.db')
    parser.add_argument('--outputdirectory', default='./airmassterms', help='Directory for plots and tables')
    parser.add_argument('--filters', nargs='+', default=list(airmasscorrection.keys()))
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
    parser.add_argument('--min-points-per-night', type=int, default=5)
    parser.add_argument('--min-airmass-span', type=float, default=0.2,
                        help='Minimum airmass range within a night to constrain the slope')
    parser.add_argument('--max-night-rms', type=float, default=0.05,
                        help='Reject nights whose residual scatter exceeds this [mag] as non-photometric')
    parser.add_argument('--min-nights', type=int, default=5, help='Minimum usable nights to report a result')
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

    data = read_zeropoints(args.database, args.filters, cameras=args.cameras, sites=args.sites, start=args.start,
                           end=args.end, cameratypes=args.cameratypes)
    if data is None:
        _logger.error("No zeropoint records found for the selection.")
        return 1

    valid = (np.isfinite(data['zp']) & np.isfinite(data['airmass']) & (data['airmass'] >= 1.) &
             (data['airmass'] < 3.) & np.isfinite(data['zpsig']) & (data['zpsig'] < args.maxzpsig) &
             ~np.isnat(data['dateobs']))
    for prefix in args.exclude_camera_prefixes:
        valid &= ~np.char.startswith(data['camera'], prefix)
    _logger.info(f"{valid.sum()} of {len(valid)} records pass basic quality cuts")
    data = {key: value[valid] for key, value in data.items()}
    # one free zeropoint per camera and night: cameras combined into an instrument group sit on different telescopes
    # with different throughput, only the extinction coefficient is shared.
    data['night'] = np.char.add(np.char.add(night_keys(data['dateobs'], data['site']), ':'), data['camera'])
    data['instrumentgroup'] = instrument_groups(data['site'], data['telescope'], data['camera'])

    for groupcolumn in ('camera', 'instrumentgroup'):
        results = analyze(data, groupcolumn, args, args.outputdirectory)
        if results is None:
            _logger.warning(f"No {groupcolumn} / filter combination had enough data for a fit.")
            continue
        basename = os.path.join(args.outputdirectory, f'airmassterms-{groupcolumn}')
        results.meta['created'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        results.meta['database'] = args.database.split('@')[-1]
        results.write(f'{basename}.ecsv', overwrite=True)
        results.write(f'{basename}.csv', overwrite=True)
        if args.plots:
            plot_summary(results, groupcolumn, args.outputdirectory)
        print(f"\nAirmass terms per {groupcolumn} and filter [mag / airmass]:")
        results.pprint_all()

    return 0


if __name__ == '__main__':
    main()
