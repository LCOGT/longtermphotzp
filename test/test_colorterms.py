import numpy as np

from longtermphotzp.colorterms import fit_colorterm, bootstrap_colorterm


def _synthetic(true_c=0.05, dcdx=0.0, nnights=30, perNight=10, outliers=True, seed=4):
    rng = np.random.default_rng(seed)
    colorterm, airmass, nights = [], [], []
    for night in range(nnights):
        # busy nights must not dominate: give every 5th night many more images with a night offset
        n = perNight * (5 if night % 5 == 0 else 1)
        offset = rng.normal(0, 0.005)
        for _ in range(n):
            X = 1 + rng.exponential(0.4)
            colorterm.append(true_c + dcdx * (X - 1) + offset + rng.normal(0, 0.02))
            airmass.append(X)
            nights.append(f'ogg:{night}:ep04')
    colorterm = np.array(colorterm)
    if outliers:
        colorterm[::37] += 0.4  # failed per-image fits
    return colorterm, np.array(airmass), np.array(nights)


def test_colorterm_is_recovered_despite_outliers():
    colorterm, airmass, nights = _synthetic()
    fit = fit_colorterm(colorterm, airmass, nights)
    assert fit is not None
    assert abs(fit['c'] - 0.05) < 0.005
    assert fit['npoints'] < len(colorterm)  # outliers clipped
    assert fit['nnights'] == 30
    cerr, dcdxerr = bootstrap_colorterm(fit, colorterm, airmass, nboot=200, rng=1)
    assert 0 < cerr < 0.005
    assert np.isfinite(dcdxerr)


def test_airmass_dependence_is_recovered():
    colorterm, airmass, nights = _synthetic(true_c=0.02, dcdx=0.03, nnights=60, outliers=False)
    fit = fit_colorterm(colorterm, airmass, nights)
    assert abs(fit['dcdx'] - 0.03) < 0.01
    assert abs(fit['c'] - 0.02) < 0.005  # reported color term is the value at airmass 1
    assert fit['c_mean'] > fit['c']  # the plain mean is biased by observations at higher airmass
    cerr, dcdxerr = bootstrap_colorterm(fit, colorterm, airmass, nboot=200, rng=1)
    assert 0 < cerr < 0.005 and 0 < dcdxerr < 0.01


def test_no_airmass_leverage_falls_back_to_mean():
    colorterm, airmass, nights = _synthetic(outliers=False)
    airmass[:] = 1.2
    fit = fit_colorterm(colorterm, airmass, nights)
    assert fit['dcdx'] == 0.
    assert abs(fit['c'] - fit['c_mean']) < 1e-12


def test_read_colorterms_selects_camera_types(tmpdir):
    from test_airmassterms import _db_with_cameras
    from longtermphotzp.colorterms import read_colorterms
    url = _db_with_cameras(tmpdir)
    data = read_colorterms(url, ['rp'], cameratypes=['ep'])
    assert sorted(data['camera']) == ['ep04', 'ep06']
    assert read_colorterms(url, ['rp'], cameratypes=['xx']) is None
