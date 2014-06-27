import requests

from .config import get_option

_BASE_URL = 'http://allmychanges.com/v1'


class ApiError(RuntimeError):
    pass


def _call(method, config, handle, data=None):
    token = get_option(config, 'token')
    base_url = get_option(config, 'base_url', _BASE_URL)

    if handle.startswith('http'):
        url = handle
    else:
        url = base_url + handle

    func = getattr(requests, method)
    response = func(url,
                    headers={'Authorization':
                             'Bearer ' + token},
                    data=data)

    if response.status_code > 400:
        raise ApiError(response.reason)

    return response.json()

_get = lambda *args, **kwargs: _call('get', *args, **kwargs)
_post = lambda *args, **kwargs: _call('post', *args, **kwargs)
_put = lambda *args, **kwargs: _call('put', *args, **kwargs)


def get_packages(config):
    return _get(config, '/packages/')

def create_package(config, pk, source):
    return _post(config, '/packages/',
                 data=dict(namespace=pk[0],
                           name=pk[1],
                           source=source))

def update_package(config, resource_uri, pk, source):
    return _put(config, resource_uri,
                 data=dict(namespace=pk[0],
                           name=pk[1],
                           source=source))


def guess_source(config, pk):
    response = _get(config, '/autocomplete-source/?namespace={0}&name={1}'.format(*pk))
    return [item['name']
            for item in response['results']]
