import sys
import click
import tablib

from .config import read_config
from .api import (get_changelogs,
                  create_changelog,
                  update_changelog,
                  track_changelog,
                  guess_source)

# first is default
_IMPORT_EXPORT_FORMATS = ('csv', 'yaml', 'json', 'xls')


def _possible_formats_str():
    return '{0} (default), {1} and {2}'.format(
        _IMPORT_EXPORT_FORMATS[0],
        ', '.join(_IMPORT_EXPORT_FORMATS[1:-1]),
        _IMPORT_EXPORT_FORMATS[-1])


def _validate_format(ctx, param, value):
    if value not in _IMPORT_EXPORT_FORMATS:
        raise click.BadParameter('Possible values are: {0}.'.format(
            _possible_formats_str()))
    return value


config_option = click.option(
    '--config',
    default='allmychanges.cfg',
    help='Config filename. Default: allmychanges.cfg.')

format_option = click.option(
    '--format',
    default=_IMPORT_EXPORT_FORMATS[0],
    callback=_validate_format,
    help='Export format. Possible values: {0}.'.format(_possible_formats_str()))


@click.command()
@click.option('--output',
              help='Output filename. By default, data is written to the stdout.')
@config_option
@format_option
def export(format, output, config):
    """Exports packages from service into the file.
    """
    config = read_config(config)
    changelogs = get_changelogs(config, tracked=True)

    fields = ('namespace', 'name', 'source')

    def extract_fields(item):
        return [item.get(key)
                for key in fields]

    data = map(extract_fields, changelogs)
    table = tablib.Dataset(*data)
    table.headers = fields
    data = getattr(table, format)
    if output:
        with open(output, 'wb') as f:
            f.write(data)
    else:
        click.echo(data)


@click.command('import')
@click.option('--input',
              help='Input filename. By default, data is read from the stdin.')
@format_option
@config_option
def _import(format, input, config):
    """Import data from file into the service.
    """
    if input:
        with open(input, 'rb') as f:
            data = f.read()
    else:
        data = sys.stdin.read()

    dataset = tablib.Dataset()
    setattr(dataset, format, data)

    _add_changelogs(config, dataset.dict)


@click.command()
@click.argument('package', nargs=-1)
@config_option
def add(package, config):
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

    _add_changelogs(config, rows)


def _add_changelogs(config, data):
    config = read_config(config)

    tracked_changelogs = {ch['resource_uri']
                          for ch in get_changelogs(config, tracked=True)}

    for row in data:
        pk = (row['namespace'], row['name'])


        if row.get('source'):
            source = row.get('source')
        else:
            click.echo('\nNo source for {0}/{1} was given, let\'s try to guess it.'.format(*pk))
            guesses = guess_source(config, namespace=pk[0], name=pk[1])

            source = None

            while not source:
                manually = False

                if guesses:
                    click.echo('Here is what I\'ve got:')
                    for idx, guess in enumerate(guesses, start=1):
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
                    source = click.prompt('Where could I find sources for {0}/{1}?'.format(*pk),
                                          prompt_suffix='\n> ')

        actions = []


        if source:
            changelogs = get_changelogs(config, source=source)
        else:
            changelogs = get_changelogs(config, namespace=pk[0], name=pk[1])

        if changelogs:
            changelog = changelogs[0]
            if source != changelog['source']:
                update_changelog(config,
                                 changelog,
                                 namespace=pk[0],
                                 name=pk[1],
                                 source=source)
                actions.append('updated')

            if changelog['resource_uri'] not in tracked_changelogs:
                track_changelog(config, changelog)
                actions.append('tracked')

        else:
            changelog = create_changelog(config, pk, source)
            track_changelog(config, changelog)
            actions.extend(['created', 'tracked'])

        if actions:
            click.echo('http://allmychanges.com/p/{namespace}/{name}/ was {actions}'.format(
                namespace=pk[0],
                name=pk[1],
                actions=' and '.join(actions)))


@click.group()
def main():
    pass

main.add_command(export)
main.add_command(_import)
main.add_command(add)
