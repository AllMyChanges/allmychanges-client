# coding: utf-8
from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import sys
import re

import click
import tablib
import pkg_resources

from collections import defaultdict
from conditions import signal, handle
from .api import (
    ApiError,
    HTTPApiError,
    get_changelogs,
    create_changelog,
    track_changelog,
    get_versions,
    get_tags,
    tag_version,
)
from .utils import (
    changelog_id,
    changelog_name,
    make_table,
    parse_project_params)


class CLIError(RuntimeError):
    pass


class ProjectNotFoundError(CLIError):
    def __init__(self, project):
        super(ProjectNotFoundError, self).__init__()
        self.message = u'Project "{0}" not found.'.format(project)


class MoreThanOneProjectFoundError(CLIError):
    def __init__(self, projects):
        super(MoreThanOneProjectFoundError, self).__init__()
        self.projects = projects
        self.message = u'More than one projects were found:' \
                       + u'\n'.join(
                           u'{namespace}/{name}'.format(**item)
                           for item in projects)


class VersionNotFoundError(CLIError):
    def __init__(self, namespace, name, version):
        super(VersionNotFoundError, self).__init__()
        self.namespace = namespace
        self.name = name
        self.version = version
        self.message = u'No such version'



NotGiven = object()


# first is default
_IMPORT_EXPORT_FORMATS = ('csv', 'yaml', 'json', 'xls')


def _possible_formats_str():
    return '{0} (default), {1} and {2}'.format(
        _IMPORT_EXPORT_FORMATS[0],
        ', '.join(_IMPORT_EXPORT_FORMATS[1:-1]),
        _IMPORT_EXPORT_FORMATS[-1])


def _max_length(text, max_length):
    if len(text) > max_length - 1:
        return text[:max_length - 1] + u'…'
    return text


def _validate_format(ctx, param, value):
    if value not in _IMPORT_EXPORT_FORMATS:
        raise click.BadParameter('Possible values are: {0}.'.format(
            _possible_formats_str()))
    return value


format_option = click.option(
    '--format',
    default=_IMPORT_EXPORT_FORMATS[0],
    callback=_validate_format,
    help='Data format. Possible values: {0}.'.format(_possible_formats_str()))


@click.group(invoke_without_command=True)
@click.option('--version',
              is_flag=True,
              help='Show current version and exit.')
@click.option('--base-url',
              help='Show current version and exit.')
@click.option('--token',
              help='Token to use when accessing AllMyChanges.com API.')
@click.pass_context
def cli(ctx, version, token, base_url):
    if token:
        ctx.obj['token'] = token

    if base_url:
        ctx.obj['base_url'] = base_url

    if version:
        distribution = pkg_resources.get_distribution('allmychanges')
        if distribution is not None:
            click.echo(u'{0.key}: {0.version}'.format(
                distribution))
            sys.exit(0)


@cli.command()
@click.option('--filename',
              help='Output filename. By default, data is written to the stdout.')
@format_option
@click.pass_context
def pull(ctx, format, filename):
    """Pulls packages from the service into the file.
    """
    changelogs = get_changelogs(ctx.obj, tracked=True)

    fields = ('namespace', 'name', 'source')

    def extract_fields(item):
        return [item.get(key)
                for key in fields]

    data = map(extract_fields, changelogs)
    table = tablib.Dataset(*data)
    table.headers = fields
    data = getattr(table, format)
    if filename:
        with open(filename, 'wb') as f:
            f.write(data)
    else:
        click.echo(data)


def show_warning_about_missing_version(e):
    click.echo(u'{0}/{1}'.format(e.namespace, e.name))
    click.echo(u'    Version {0} not found. '
               u'Tag will be bound to the version when '
               u'it will be discovered.'.format(e.version))


@cli.command()
@click.option('--filename',
              help='Input filename. By default, data is read from the stdin.')
@format_option
@click.pass_context
def push(ctx, format, filename):
    """Gets data from a file and pushes it into the service.
    """
    if filename:
        with open(filename, 'rb') as f:
            data = f.read()
    else:
        data = sys.stdin.read()

    dataset = tablib.Dataset()
    setattr(dataset, format, data)
    parsed_data = dataset.dict
    # filter out empty lines
    parsed_data = filter(None, parsed_data)

    try:
        _add_changelogs(ctx.obj, parsed_data)

        with handle(VersionNotFoundError,
                    show_warning_about_missing_version):
            _tag_versions(ctx.obj, parsed_data)

    except HTTPApiError as e:
        if e.response.status_code == 401:
            click.echo('Please provide valid OAuth token in AMCH_TOKEN environment variable')
        else:
            raise


@cli.command()
@click.argument('package', nargs=-1)
@click.pass_context
def add(ctx, package):
    """Adds one or more packages.

    Here PACKAGE is a string in <namespace>/<package>
    or <namespace>/<package>/<source> format.
    """

    def parse_package(text):
        splitted = text.split('/', 2)
        if len(splitted) == 3:
            namespace, name, source = splitted
        else:
            namespace, name = splitted
            source = None
        return dict(namespace=namespace,
                    name=name,
                    source=source)

    rows = map(parse_package, package)

    _add_changelogs(ctx.obj, rows)


def _add_changelogs(opts, data):

    tracked_changelogs = get_changelogs(opts, tracked=True)
    tracked_changelogs = dict(
        ((ch['namespace'], ch['name']), ch)
        for ch in tracked_changelogs)

    def is_tracked(changelog):
        return (changelog['namespace'],
                changelog['name']) in tracked_changelogs

    for row in data:
        if not row:
            continue
        changelog = None
        namespace, name = (row['namespace'], row['name'])
        source = row.get('source')
        # значит, логика добавления changelog такая:
        # во входных данных всегда должны присутствовать namespace и name
        # так как это уникальный идентификатор пакета в allmychanges.
        # Поле source опционально, если оно есть, то производятся
        # дополнительные проверки и выводятся дополнительные предупреждения
        # со стороны allmychanges пакет может быть в трех состояниях:
        # 1. отсутствует
        #    - если source не указан, то запустить guesser и попросить выбрать URL
        #    - добавить пакет
        # 2. есть, но не затрекан
        #    - если source указан и не такой как в allmychanges, показать предупреждение
        #    - затрекать
        # 3. есть и затрекан
        #    - если source указан, то  проверить, что source затреканного такой же
        #      и если нет, то вывести предупреждение

        # searching changelog in allmychange's database
        changelogs = get_changelogs(opts,
                                    namespace=namespace,
                                    name=name)
        if changelogs:
            changelog = changelogs[0]
        else:
            changelog = None

        actions = []

        if changelog is None:

            changelog = create_changelog(
                opts,
                namespace,
                name,
                source=source)

            if source is None:
                actions.append('added without source url')
            else:
                actions.append('created')

            track_changelog(opts, changelog)
            actions.append('tracked')
        else:
            if is_tracked(changelog):
                if source and source != changelog['source']:
                    click.echo(
                        ('Warning! You already tracking package '
                         '{0[namespace]}/{0[name]}, '
                         'but with url {0[source]}.'
                     ).format(changelog))
            else:
                if source and source != changelog['source']:
                    click.echo(
                        ('Warning! You there is package '
                         '{0[namespace]}/{0[name]} in database, '
                         'but with url {0[source]}.'
                     ).format(changelog))
                track_changelog(opts, changelog)
                actions.append('tracked')

        if actions:
            click.echo('http://allmychanges.com/p/{namespace}/{name}/ was {actions}'.format(
                namespace=namespace,
                name=name,
                actions=' and '.join(actions)))


def _tag_version(opts, namespace, name, version, tag):
    project_params = (('namespace', namespace),
                      ('name', name))
    project_params = {key: value
                      for key, value in project_params
                      if value is not None}

    projects = get_changelogs(opts, **project_params)

    if not projects:
        signal(ProjectNotFoundError(u'{0}/{1}'.format(namespace, name)))
    else:
        if len(projects) > 1:
            signal(MoreThanOneProjectFoundError(projects))
        else:
            project = projects[0]
            versions = get_versions(
                opts,
                project,
                number=version)

            if len(versions) == 0:
                signal(
                    VersionNotFoundError(namespace,
                                         name,
                                         version))

            tag_version(opts, project, tag, version)


def _tag_versions(opts, data):
    for item in data:
        version = item['version']
        tag = item['tag']
        if version and tag:
            _tag_version(opts,
                         item['namespace'],
                         item['name'],
                         version,
                         tag)



@cli.command()
@click.argument('query')
@click.pass_context
def search(ctx, query):
    """Searches project or namespace on the service.

    Here query can be a string in <namespace> or <namespace>/<package>
    form.
    """
    if '/' in query:
        namespace, name = query.split('/', 1)
        changelogs = get_changelogs(ctx.obj,
                                    namespace=namespace,
                                    name=name)
    else:
        changelogs = get_changelogs(ctx.obj,
                                    namespace=query)
        if not changelogs:
            changelogs = get_changelogs(ctx.obj,
                                        name=query)


    data = []
    for ch in changelogs:
        data.append([
            ch['namespace'],
            ch['name'],
            ch['latest_version'] or '',
            _max_length(ch['description'], 80) or 'no description'])

    table = make_table(
        ['namespace', 'name', 'version', 'description'],
        data,
        no_wrap=['namespace', 'name', 'version'])
    click.echo(table)


@cli.command()
@click.argument('project')
@click.argument('version')
@click.argument('tag')
@click.pass_context
def tag(ctx, project, version, tag):
    """Marks some project's version with given tag.

    Usually, tag is a project name where tagged version is used.
    For example:

    amch tag python/django 1.8.10 allmychanges.com

    You can use command 'amch tags' to list all tags and corresponded projects.
    """
    try:
        opts = ctx.obj

        project_params = parse_project_params(project)
        project_obj = get_changelogs(opts, **project_params)

        if not project_obj:
            click.echo(u'Project "{0}" not found.'.format(
                project))

        project_obj = project_obj[0]

        def print_error(e):
            click.echo('ERROR: {0.message}'.format(e))

        with handle(CLIError,
                    print_error), \
             handle(VersionNotFoundError,
                    show_warning_about_missing_version):

            _tag_version(opts,
                         project_obj['namespace'],
                         project_obj['name'],
                         version,
                         tag)

    except ApiError as e:
        report_api_error(e)


@cli.command()
@click.pass_context
@click.option('--filter',
              'filter_regex',
              help='Show only tags matching regex.')
def tags(ctx, filter_regex):
    """Outputs all tags along with tagged project versions.
    """
    try:
        opts = ctx.obj
        tags = list(get_tags(opts))

        changelog_ids = set(tag['changelog']
                            for tag in tags)
        changelog_ids = ','.join(map(unicode, changelog_ids))
        changelogs = get_changelogs(opts, id__in=changelog_ids)

        changelogs = {changelog_id(ch): ch for ch in changelogs}
        tagged_changelogs = defaultdict(list)

        if filter_regex:
            filter_re = re.compile('^{0}$'.format(filter_regex))
            passes_filter = filter_re.match
        else:
            passes_filter = lambda tag_name: True


        for tag in tags:
            tag_name = tag['name']
            if passes_filter(tag_name):
                tagged_changelogs[tag_name].append(
                    (changelogs[tag['changelog']], tag['version_number'])
                )

        items = tagged_changelogs.items()
        items.sort()

        def tagged_project_name(item):
            ch, number = item
            return u'{0}:{1}'.format(
                changelog_name(ch),
                number)

        data = []
        for name, changelogs in items:
            changelogs.sort()

            data.append(
                (name,
                 ', '.join(
                     map(tagged_project_name, changelogs))))

        table = make_table(
            ['tag', 'versions'],
            data,
            no_wrap=['tag'],
            hrules=True)
        click.echo(table)

    except ApiError as e:
        raise
        report_api_error(e)


@cli.command()
@click.argument('project')
@click.pass_context
def versions(ctx, project):
    """Outputs all known versions of a given project.

    If project is tagged, then it's tags are printed too.
    """
    try:
        opts = ctx.obj
        project_params = parse_project_params(project)
        project_obj = get_changelogs(opts, **project_params)

        if not project_obj:
            click.echo('Project "{0}" not found.'.format(project))
        else:
            project_obj = project_obj[0]

        versions = get_versions(opts, project_obj)
        tags = get_tags(opts, project_obj)

        tag_by_version = defaultdict(list)

        for t in tags:
            tag_by_version[t['version_number']].append(t)

        for version in versions:
            number = version['number']
            tags = tag_by_version[number]
            if tags:
                click.echo(u'{number}: {tags}'.format(
                    number=number,
                    tags=u', '.join(
                        t['name'] for t in tags)))
            else:
                click.echo(number)

    except ApiError as e:
        report_api_error(e)


def report_api_error(e):
    if e.response.status_code == 500:
        request_id = e.response.headers['x-request-id']
        click.echo(
            'API returned "Unhandled error" with 500 status code.\n'
            'Please, write to support@allmychanges.com '
            'and describe the situation.\n'
            'Providing this unique code will help us '
            'to investigate our logs: {0}'.format(request_id))
    else:
        try:
            data = e.response.json()
            click.echo(data['detail'])
        except:
            click.echo('Unknown error')


def main():
    cli(auto_envvar_prefix='AMCH',
        obj={})
