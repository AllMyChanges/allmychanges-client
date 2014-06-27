import ConfigParser

_NotGiven = object()


def read_config(filename='allmychanges.cfg'):
    config = ConfigParser.SafeConfigParser()
    config.read(filename)
    return config


def get_option(config, name, default=_NotGiven):
    try:
        return config.get('allmychanges', name)
    except ConfigParser.NoOptionError:
        if default is _NotGiven:
            raise
        return default
