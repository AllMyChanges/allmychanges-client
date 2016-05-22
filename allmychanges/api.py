# coding: utf-8

import requests

from six.moves.urllib.parse import urlencode
from conditions import signal, handle
from .utils import (
    changelog_id,
    parse_project_params,
    only_keys)


_BASE_URL = 'https://allmychanges.com/v1'


def force_str(text):
    # TODO: use types from six
    if isinstance(text, unicode):
        return text.encode('utf-8')
    return text


class ApiError(RuntimeError):
    pass


class HTTPApiError(ApiError):
    def __init__(self, message, response):
        verbose_message = u'{0}: {1}'.format(message, response.content)
        super(ApiError, self).__init__(verbose_message)
        self.response = response


class DownloaderAndSourceError(ApiError):
    pass


class NamespaceNameAlreadyExists(RuntimeError):
    def __init__(self, namespace, name):
        super(NamespaceNameAlreadyExists, self).__init__(
            'Project {0}/{1} already exists'.format(
                namespace, name))
        self.namespace = namespace
        self.name = name


class SourceAlreadyExists(RuntimeError):
    def __init__(self, url):
        super(SourceAlreadyExists, self).__init__(
            'Project with source {0} already exists'.format(url))
        self.source = url


class AuthenticationRequired(RuntimeError):
    pass


def _call(method, opts, handle, data=None):
    token = opts.get('token')
    base_url = opts.get('base_url', _BASE_URL)
    debug = opts.get('debug', False)

    if handle.startswith('http'):
        url = handle
    else:
        url = base_url + handle

    func = getattr(requests, method)
    if token:
        headers={'Authorization': 'Bearer ' + token}
    else:
        headers={}

    response = func(url, headers=headers, data=data)

    if debug:
        if response.status_code >= 300:
            description = response.reason
        else:
            description = ''
        print(u'{0} {1} → {2} {3}'.format(
            method.upper(), url,
            response.status_code, description).encode('utf-8'))

    if response.status_code >= 400:
        signal(HTTPApiError(response.reason, response))

    return response.json()

_get = lambda *args, **kwargs: _call('get', *args, **kwargs)
_post = lambda *args, **kwargs: _call('post', *args, **kwargs)
_put = lambda *args, **kwargs: _call('put', *args, **kwargs)


def _get_all(opts, handle, **kwargs):
    """Returns an iterator over all objects returned by
    given handle. Traverses multiply pages, making
    as many requests as requred.
    """
    response = _get(opts, handle, **kwargs)

    while True:
        for item in response['results']:
            yield item

        next_url = response.get('next')
        if next_url is None:
            break

        response = _get(opts, next_url, **kwargs)


def require_authentication(opts):
    """This call will raise HTTPApiError if user is not authenticated."""
    _get(opts, '/user/')


def get_changelogs(opts, **params):
    """Returns list of changelogs.
    Params could be: namespace and name or tracked=True
    """
    handle = '/changelogs/'
    params = {key: force_str(value)
              for key, value in params.items()}
    url = handle + '?' + urlencode(params)
    return _get(opts, url)


def get_versions(opts, project, number=None):
    handle = '/versions/'
    if isinstance(project, basestring):
        project_params = parse_project_params(project)
    else:
        project_params = only_keys(project, 'namespace', 'name')

    params = {'changelog__' + name: value
              for name, value in project_params.items()}

    if number is not None:
        params['number'] = number

    url = handle + '?' + urlencode(params)
    data = _get(opts, url)
    results = data['results']
    return results


def tag_version(opts, project, tag, version_number):
    require_authentication(opts)

    uri = project['resource_uri']
    return _post(opts,
                 uri + u'tag/',
                 data=dict(name=tag,
                           version=version_number))


def get_tags(opts, project=None):
    """Returns iterator over all tags.
    """
    require_authentication(opts)

    handle = '/tags/'
    params = {}
    if project:
        params['project_id'] = changelog_id(project)

    return _get_all(opts, handle)


def create_changelog(opts,
                     namespace,
                     name,
                     source=None,
                     downloader=None):
    require_authentication(opts)

    def handle_api_error(e):
        data = e.response.json()
        if 'Changelog with this Namespace and Name already exists' in data.get('__all__', [''])[0]:
            signal(NamespaceNameAlreadyExists(namespace, name))
        elif 'already exists' in data.get('source', [''])[0]:
            signal(SourceAlreadyExists(source))

        signal(e)

    with handle(HTTPApiError, handle_api_error):
        data = dict(namespace=namespace,
                    name=name)
        if source and not downloader or \
           downloader and not source:
            signal(DownloaderAndSourceError('Both downloader and source are required'))

        if source and downloader:
            data['source'] = source
            data['downloader'] = 'downloader'

        return _post(opts, '/changelogs/', data=data)


def update_changelog(opts, changelog, namespace, name, source):
    require_authentication(opts)

    return _put(opts, changelog['resource_uri'],
                 data=dict(namespace=namespace,
                           name=name,
                           source=source))


def untrack_changelog(opts, changelog):
    require_authentication(opts)

    return _post(opts, changelog['resource_uri'] + 'untrack/')


def track_changelog(opts, changelog):
    require_authentication(opts)

    return _post(opts, changelog['resource_uri'] + 'track/')


def guess_source(opts, namespace, name):
    response = _get(opts, '/search-autocomplete/?' + urlencode(
        dict(q='{0}/{1}'.format(namespace, name))))
    return [item['source']
            for item in response['results']]


def search_category(opts, namespace):
    """
    Returns packages of namespace(category)
    :param opts:
    :param namespace:
    :return:
    """
    handle = '/changelogs/'
    return _get(opts, handle + '?' + urlencode(dict(namespace=namespace)))
