# coding: utf-8
import sys

import click
import tablib
import pkg_resources

from collections import defaultdict
from .api import (ApiError,
                  get_changelogs,
                  create_changelog,
                  track_changelog,
                  get_versions,
                  get_tags,
                  tag_version,
                  guess_source)
from .utils import (
    changelog_id,
    changelog_name,
    parse_project_params)


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

    _add_changelogs(ctx.obj, dataset.dict)


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

    def ask_about_source(namespace, name):
        click.echo(
            ('\nNo source for {0}/{1} was given, '
             'let\'s try to guess it.').format(
                 namespace, name))
        guesses = guess_source(
            opts, namespace=namespace, name=name)

        source = None
        while not source:
            manually = False

            if guesses:
                click.echo('Here is what I\'ve got:')
                for idx, guess in enumerate(
                        guesses, start=1):
                    click.echo('{0}) {1}'.format(idx, guess))
                click.echo('0) enter manually')

                def validate_choice(value):
                    try:
                        value = int(value)
                    except ValueError:
                        raise click.BadParameter('You entered invalid number.')

                    if value < 0 or value > len(guesses):
                        raise click.BadParameter('Please, make a correct choice.')

                    return value

                choice = click.prompt('Please, select option [0-{0}]'.format(len(guesses)),
                                      value_proc=validate_choice)
                if choice == 0:
                    manually = True
                else:
                    source = guesses[choice - 1]
            else:
                manually = True

            if manually:
                source = click.prompt(
                    ('Where could I find sources for {0}/{1}? '
                     '(type "skip" to skip this package)')
                    .format(namespace, name),
                    prompt_suffix='\n> ')
        return source

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
            if source is None:
                source = ask_about_source(namespace, name)

            if source == 'skip':
                actions.append('skipped')
            else:
                changelog = create_changelog(
                    opts, namespace, name, source)
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
            ch['latest_version'],
            _max_length(ch['description'], 80) or 'no description'])

    table = tablib.Dataset(*data)
    table.headers = ['namespace', 'name', 'version', 'description']
    click.echo(table.tsv)


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
        else:
            if len(project_obj) > 1:
                click.echo(u'More than one "{0}" were found:'.format(
                    project))
                for item in project_obj:
                    click.echo(u'{namespace}/{name}'.format(**item))
            else:
                versions = get_versions(
                    opts,
                    project_obj[0],
                    number=version)

                if len(versions) == 0:
                    click.echo(u'No such version')
                    return 1

                version_obj = versions[0]
                tag_version(opts, version_obj, tag)
    except ApiError as e:
        report_api_error(e)


@cli.command()
@click.pass_context
def tags(ctx):
    """Outputs all tags along with tagged project versions.
    """
    try:
        opts = ctx.obj
        tags = get_tags(opts)
        changelog_ids = set(tag['changelog']
                            for tag in tags)
        changelogs = get_changelogs(
            opts,
            id__in=','.join(map(unicode, changelog_ids)))

        changelogs = {changelog_id(ch): ch for ch in changelogs}
        tagged_changelogs = defaultdict(list)

        for tag in tags:
            tagged_changelogs[tag['name']].append(
                (changelogs[tag['changelog']], tag['version_number'])
            )

        items = tagged_changelogs.items()
        items.sort()

        def tagged_project_name(item):
            ch, number = item
            return u'{0}:{1}'.format(
                changelog_name(ch),
                number)

        for name, changelogs in items:
            changelogs.sort()

            click.echo(u'{tag}: {changelogs}'.format(
                tag=name,
                changelogs=u', '.join(
                    map(tagged_project_name, changelogs))))

    except ApiError as e:
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
