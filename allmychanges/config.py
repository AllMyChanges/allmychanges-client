
import sys
if sys.version_info > (3, 0):
    from configparser import ConfigParser, NoOptionError
else:
    from ConfigParser import SafeConfigParser as ConfigParser, NoOptionError

_NotGiven = object()

def read_config(filename='allmychanges.cfg'):
    config = ConfigParser()
    config.read(filename)
    return config


def get_option(config, name, default=_NotGiven):
    try:
        return config.get('allmychanges', name)
    except NoOptionError:
        if default is _NotGiven:
            raise
        return default
