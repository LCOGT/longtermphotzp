import datetime

import longtermphotzp.webapp as webapp


def _render(path='/'):
    # render through the route function; avoids Flask's test client, which needs a matching werkzeug version
    with webapp.app.test_request_context(path):
        return webapp.indexhtml()


def _stub_s3(monkeypatch):
    monkeypatch.setattr(webapp, 'get_last_update_time_from_object', lambda: datetime.datetime(2026, 10, 20))
    monkeypatch.setattr(webapp, 'build_site_info_dict', lambda filter=None: {})
    monkeypatch.setattr(webapp, 'generate_presigned_url', lambda filename: f'https://example.invalid/{filename}')


def test_index_shows_release_version(monkeypatch):
    _stub_s3(monkeypatch)
    monkeypatch.setattr(webapp, 'RELEASE_VERSION', '8.4.0')
    html = _render()
    assert '<h1>LCO Zeropoint Plots <small class="text-muted">v8.4.0</small></h1>' in html
    assert '<title>LCO Zeropoint Plots 8.4.0</title>' in html


def test_index_without_version(monkeypatch):
    _stub_s3(monkeypatch)
    monkeypatch.setattr(webapp, 'RELEASE_VERSION', None)
    html = _render()
    assert '<h1>LCO Zeropoint Plots</h1>' in html


def test_release_version_is_the_installed_package_version():
    from importlib.metadata import version
    assert webapp.get_release_version() == version('longtermphotzp')
