# coding: utf-8

import requests

from urllib import urlencode
from .config import get_option

_BASE_URL = 'http://allmychanges.com/v1'


class ApiError(RuntimeError):
    def __init__(self, message, response):
        verbose_message = u'{0}: {1}'.format(message, response.content)
        super(ApiError, self).__init__(verbose_message)
        self.response = response


class AlreadyExists(RuntimeError):
    def __init__(self, namespace, name):
        super(AlreadyExists, self).__init__(
            'Package {0}/{1} already exists'.format(
                namespace, name))
        self.namespace = namespace
        self.name = name


def _call(method, config, handle, data=None):
    token = get_option(config, 'token')
    base_url = get_option(config, 'base_url', _BASE_URL)
    debug = get_option(config, 'debug', False)

    if handle.startswith('http'):
        url = handle
    else:
        url = base_url + handle

    func = getattr(requests, method)
    response = func(url,
                    headers={'Authorization':
                             'Bearer ' + token},
                    data=data)

    if debug:
        if response.status_code >= 300:
            description = response.reason
        else:
            description = ''
        print u'{0} {1} → {2} {3}'.format(
            method.upper(), url,
            response.status_code, description).encode('utf-8')

    if response.status_code >= 400:
        raise ApiError(response.reason, response)

    return response.json()

_get = lambda *args, **kwargs: _call('get', *args, **kwargs)
_post = lambda *args, **kwargs: _call('post', *args, **kwargs)
_put = lambda *args, **kwargs: _call('put', *args, **kwargs)


def get_changelogs(config, **params):
    """Returns list of changelogs.
    Params could be: namespace and name or tracked=True
    """
    handle = '/changelogs/'
    return _get(config, handle + '?' + urlencode(params))


def create_changelog(config, namespace, name, source):
    try:
        return _post(config, '/changelogs/',
                     data=dict(namespace=namespace,
                               name=name,
                               source=source))
    except ApiError as e:
        data = e.response.json()
        if 'Changelog with this Namespace and Name already exists' in data.get('__all__', [''])[0]:
            raise AlreadyExists(namespace, name)
        raise


def update_changelog(config, changelog, namespace, name, source):
    return _put(config, changelog['resource_uri'],
                 data=dict(namespace=namespace,
                           name=name,
                           source=source))


def track_changelog(config, changelog):
    return _post(config, changelog['resource_uri'] + 'track/')


def guess_source(config, namespace, name):
    response = _get(config, '/search-autocomplete/?' + urlencode(
        dict(q='{0}/{1}'.format(namespace, name))))
    return [item['source']
            for item in response['results']]
