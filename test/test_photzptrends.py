import datetime

import numpy as np

from longtermphotzp.photzptrends import findUpperEnvelope


def _nights(nnights, perNight, start=datetime.datetime(2024, 1, 1, 14), zp=23.5, sigma=0.0):
    rng = np.random.default_rng(0)
    dates, zps = [], []
    for night in range(nnights):
        for frame in range(perNight):
            dates.append(start + datetime.timedelta(days=night, hours=8 * frame / perNight))
            zps.append(zp + rng.normal(0, sigma))
    return np.asarray(dates), np.asarray(zps)


def test_brightest_point_of_night_is_rejected():
    dates, zps = _nights(20, 10)
    zps[::10] += 0.5  # one bright outlier every night
    _, model = findUpperEnvelope(dates, zps, ymax=25, site='tfn')
    np.testing.assert_allclose(model, 23.5, atol=1e-6)


def test_most_recent_model_points_are_not_biased_low():
    dates, zps = _nights(30, 10)
    zps += 0.01 * (dates - dates[0]).astype('timedelta64[s]').astype(float) / 86400.  # rising throughput
    x, model = findUpperEnvelope(dates, zps, ymax=25, site='tfn')
    assert model[-1] >= model[-5]
    assert abs(model[-1] - (23.5 + 0.01 * 29)) < 0.05


def test_night_is_not_split_at_12utc_for_coj():
    # coj night runs ~09-19 UTC; 6 frames straddling 12 UTC must end up in one night
    start = datetime.datetime(2024, 1, 1, 9)
    dates = np.asarray([start + datetime.timedelta(hours=2 * i) for i in range(6)])
    zps = np.full(len(dates), 23.5)
    x, model = findUpperEnvelope(dates, zps, ymax=25, site='coj')
    assert len(x) == 1


def test_nan_values_are_ignored():
    dates, zps = _nights(5, 10)
    zps[3] = np.nan
    _, model = findUpperEnvelope(dates, zps, ymax=25, site='lsc')
    assert np.all(np.isfinite(model))


def test_color_term_summary_without_color_terms(tmpdir):
    from types import SimpleNamespace
    from longtermphotzp.photzptrends import plot_all_color_terms
    context = SimpleNamespace(filter='rp', imagedbPrefix=str(tmpdir))
    plot_all_color_terms(context, {})
    plot_all_color_terms(context, {'rp': {'ogg-clma-2m0a': 0.05}})
    assert len(tmpdir.listdir()) == 0


def test_site_airmass_correction_with_fallback():
    from longtermphotzp.photzptrends import getairmasscorrection, siteairmasscorrection, airmasscorrection
    assert getairmasscorrection('lsc', 'gp') == siteairmasscorrection['lsc']['gp']
    assert getairmasscorrection('ogg', 'B') == airmasscorrection['B']  # no site value: default
    assert getairmasscorrection('xyz', 'rp') == airmasscorrection['rp']  # unknown site: default
    assert getairmasscorrection('tfn', 'zp') == siteairmasscorrection['tfn']['zs']  # zp shares the zs value
    assert getairmasscorrection('lsc', 'Rc') == airmasscorrection['Rc']
