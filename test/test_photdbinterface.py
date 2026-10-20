import math

import numpy as np

from longtermphotzp.photdbinterface import photdbinterface, PhotZPMeasurement


def test_sq_camera_gain_correction_april_2026(tmpdir):
    db = photdbinterface(f"sqlite:///{tmpdir}/test.db")
    for name, dateobs, camera in (('before', '2026-04-08T08:00:00', 'sq34'),
                                  ('inside', '2026-04-20T03:00:00', 'sq34'),
                                  ('after', '2026-05-05T23:00:00', 'sq34'),
                                  ('othercam', '2026-04-20T03:00:00', 'fa05')):
        db.addphotzp(PhotZPMeasurement(name=name, dateobs=dateobs, site='lsc', dome='aqwa', telescope='0m4a',
                                       camera=camera, filter='rp', airmass=1.0, zp=21.0, colorterm=0.0,
                                       zpsig=0.05))
    t = db.readRecords(site='lsc', filter=['rp'])
    db.close()
    zp = dict(zip(t['name'], t['zp']))
    np.testing.assert_allclose(zp['inside'], 21.0 - 2.5 * math.log10(2))
    for name in ('before', 'after', 'othercam'):
        np.testing.assert_allclose(zp[name], 21.0)
