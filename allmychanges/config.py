# coding: utf-8

from six.moves.configparser import ConfigParser, NoOptionError

_NotGiven = object()


def get_option(ctx, name, default=_NotGiven):
    try:
        return ctx.obj[name]
    except KeyError:
        if default is _NotGiven:
            raise
        return default
