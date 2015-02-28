# coding: utf-8
import sys
import click
import tablib

from .config import read_config
from .api import (get_changelogs,
                  create_changelog,
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

    tracked_changelogs = get_changelogs(config, tracked=True)
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
            config, namespace=namespace, name=name)

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
        changelogs = get_changelogs(config,
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
                        config, namespace, name, source)
                    actions.append('created')

                    track_changelog(config, changelog)
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
                track_changelog(config, changelog)
                actions.append('tracked')


        if actions:
            click.echo('http://allmychanges.com/p/{namespace}/{name}/ was {actions}'.format(
                namespace=namespace,
                name=name,
                actions=' and '.join(actions)))


@click.group()
def main():
    pass

main.add_command(export)
main.add_command(_import)
main.add_command(add)
