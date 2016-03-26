# coding: utf-8

import requests

from six.moves.urllib.parse import urlencode

from .utils import (
    changelog_id,
    parse_project_params,
    only_keys)


_BASE_URL = 'http://allmychanges.com/v1'


def force_str(text):
    # TODO: use types from six
    if isinstance(text, unicode):
        return text.encode('utf-8')
    return text


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
        raise ApiError(response.reason, response)

    return response.json()

_get = lambda *args, **kwargs: _call('get', *args, **kwargs)
_post = lambda *args, **kwargs: _call('post', *args, **kwargs)
_put = lambda *args, **kwargs: _call('put', *args, **kwargs)


def get_changelogs(opts, **params):
    """Returns list of changelogs.
    Params could be: namespace and name or tracked=True
    """
    handle = '/changelogs/'
    try:
        params = {key: force_str(value)
                  for key, value in params.items()}
        url = handle + '?' + urlencode(params)
    except:
        # import pdb; pdb.set_trace()  # DEBUG
        raise
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


def tag_version(opts, version, tag):
    pk = version['id']
    return _post(opts,
                 u'/versions/{0}/tag/'.format(pk),
                 data=dict(name=tag))


def get_tags(opts, project=None):
    handle = '/tags/'
    params = {}
    if project:
        params['project_id'] = changelog_id(project)
    data = _get(opts, handle)
    results = data['results']
    return results


def create_changelog(opts, namespace, name, source):
    try:
        return _post(opts,
                     '/changelogs/',
                     data=dict(namespace=namespace,
                               name=name,
                               source=source))
    except ApiError as e:
        data = e.response.json()
        if 'Changelog with this Namespace and Name already exists' in data.get('__all__', [''])[0]:
            raise AlreadyExists(namespace, name)
        raise


def update_changelog(opts, changelog, namespace, name, source):
    return _put(opts, changelog['resource_uri'],
                 data=dict(namespace=namespace,
                           name=name,
                           source=source))


def untrack_changelog(opts, changelog):
    return _post(opts, changelog['resource_uri'] + 'untrack/')


def track_changelog(opts, changelog):
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
