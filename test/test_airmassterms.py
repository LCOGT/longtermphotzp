import numpy as np

from longtermphotzp.airmassterms import fit_airmass_term, bootstrap_k, night_keys, instrument_groups


def test_fit_recovers_airmass_term_despite_drift_and_clouds():
    rng = np.random.default_rng(3)
    true_k = 0.12
    airmass, zp, nights = [], [], []
    for night in range(60):
        zp0 = 23.0 - 0.002 * night + rng.normal(0, 0.05)  # throughput drift and nightly offsets
        cloudy = night % 5 == 0
        for _ in range(15):
            X = 1 + rng.exponential(0.4)
            z = zp0 - true_k * X + rng.normal(0, 0.01)
            if cloudy:
                z -= rng.exponential(0.3)
            airmass.append(X)
            zp.append(z)
            nights.append(f'lsc:{night}')

    fit = fit_airmass_term(np.array(airmass), np.array(zp), np.array(nights))
    assert fit is not None
    assert abs(fit['k'] - true_k) < 0.005
    assert fit['nnights'] < 60  # cloudy nights are rejected
    assert 0 < bootstrap_k(fit, nboot=100, rng=1) < 0.01


def test_night_keys_group_a_local_night():
    # 23:00 and 05:00 local time at lsc (UTC-4.7h) belong to the same night, 13:00 local the next day does not.
    dateobs = np.array(['2024-03-01T03:43', '2024-03-01T09:43', '2024-03-01T17:43'], dtype='datetime64[ms]')
    keys = night_keys(dateobs, np.array(['lsc'] * 3))
    assert keys[0] == keys[1] == 'lsc:2024-02-29'
    assert keys[2] == 'lsc:2024-03-01'


def test_instrument_groups_combine_camera_type_and_telescope_class():
    groups = instrument_groups(np.array(['lsc', 'lsc', 'ogg']), np.array(['1m0a', '1m0a', '2m0a']),
                               np.array(['fa15', 'fa04', 'ep04']))
    assert list(groups) == ['lsc-1m0-fa', 'lsc-1m0-fa', 'ogg-2m0-ep']
