# coding: utf-8

import os
from prettytable import PrettyTable
from operator import itemgetter


def only_keys(d, *keys):
    return {
        key: value
        for key, value in d.items()
        if key in keys}


def parse_project_params(project):
    if '/' in project:
        namespace, name = project.split('/', 1)
        return dict(
            namespace=namespace,
            name=name)

    return dict(name=project)


def changelog_name(ch):
    return u'{0[namespace]}/{0[name]}'.format(ch)


# TODO: make normal uri schemes along with ids
def changelog_id(ch):
    return int(ch['resource_uri'].strip('/').rsplit('/', 1)[-1])


def get_terminal_width():
    rows, columns = os.popen('stty size', 'r').read().split()
    return int(columns)


def make_table(headers, data, no_wrap=[], hrules=False):
    from prettytable import ALL, HEADER, NONE

    max_width = get_terminal_width()
    table = PrettyTable(max_table_width=max_width)
    table.field_names = headers
    table.align = 'l'

    for row in data:
        table.add_row(row)

    if data:
        for fieldname in no_wrap:
            idx = headers.index(fieldname)
            column_data = map(itemgetter(idx), data)
            min_column_width = max(map(len, column_data))
            table._min_width[fieldname] = min_column_width
    opts = {}
    if hrules:
        opts['hrules'] = ALL

    return table.get_string(**opts)
