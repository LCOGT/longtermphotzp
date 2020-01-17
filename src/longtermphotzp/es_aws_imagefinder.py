from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search


def make_elasticsearch(index, filters, queries=None, exclusion_filters=None, range_filters=None, prefix_filters=None,
                       terms_filters=None,
                       es_url='http://elasticsearch.lco.gtn:9200'):
    """
    Make an ElasticSearch query

    Parameters
    ----------
    index : str
            Name of index to search
    filters : list of dicts
              Each dict has a criterion for an ElasticSearch "filter"
    queries : list of dicts
              Each dict has a "type" and "query" entry. The 'query' entry is a dict that has a criterion for an
              ElasticSearch "query"
    exclusion_filters : list of dicts
                        Each dict has a criterion for an ElasticSearch "exclude"
    range_filters: list of dicts
                   Each dict has a criterion an ElasticSearch "range filter"
    es_url : str
             URL of the ElasticSearch host

    Returns
    -------
    search : elasticsearch_dsl.Search
             The ElasticSearch object
    """
    if queries is None:
        queries = []
    if exclusion_filters is None:
        exclusion_filters = []
    if range_filters is None:
        range_filters = []
    if terms_filters is None:
        terms_filters = []
    if prefix_filters is None:
        prefix_filters = []
    es = Elasticsearch(es_url)
    s = Search(using=es, index=index)
    for f in filters:
        s = s.filter('term', **f)
    for f in terms_filters:
        s = s.filter('terms', **f)
    for f in range_filters:
        s = s.filter('range', **f)
    for f in prefix_filters:
        s = s.filter('prefix', **f)
    for f in exclusion_filters:
        s = s.exclude('term', **f)
    for q in queries:
        s = s.query(q['type'], **q['query'])
    return s


def get_frames_for_photometry(dayobs, site=None, cameratype=None, camera=None, mintexp=30,
                              filterlist=['gp', 'rp', 'ip', 'zp'], es_url='http://elasticsearch.lco.gtn:9200'):

    """ Queries for a list of processed LCO images that are viable to get a photometric zeropoint in the griz bands measured.

        Selection criteria are by DAY-OBS, site, by camaera type (fs,fa,kb), what filters to use, and minimum exposure time.
        Only day-obs is a mandatory fields, we do not want to query the entire archive at once.
     """

    # TODO: further preselect by number of sources to avoid overly crowded or empty fields
    query_filters = [{'DAY-OBS': dayobs}, {'RLEVEL': 91}, {'WCSERR': 0}, ]
    range_filters = [{'EXPTIME': {'gte': mintexp}}, ]
    terms_filters = [{'FILTER': filterlist}]
    prefix_filters = []

    if site is not None:
        query_filters.append({'SITEID': site})
    if camera is not None:
        query_filters.append({'INSTRUME': camera})
    if cameratype is not None:
        prefix_filters.append({'INSTRUME': cameratype})

    queries = []
    records = make_elasticsearch('fitsheaders', query_filters, queries, exclusion_filters=None, es_url=es_url,
                                 range_filters=range_filters, prefix_filters=prefix_filters,
                                 terms_filters=terms_filters).scan()
    records_sanitized = [record['filename']
                           for record in records]
    return records_sanitized