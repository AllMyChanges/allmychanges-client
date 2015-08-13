# -*- encoding: utf-8 -*-

from allmychanges.api import search_category, track_changelog, get_changelogs
from allmychanges.config import read_config


def main():
    config = read_config()

    section = 'python'

    changelogs = get_changelogs(config, tracked=True)
    subscribed_packages = [x['name'] for x in changelogs
                           if 'namespace' in x and x['namespace'] == section]

    python_libraries = search_category(config, section)

    all_cnt = len(python_libraries)

    for i, x in enumerate(python_libraries):
        if i % 10 == 0:
            print("Process: %s of %s" % (i, all_cnt))

        if not (x.get('name') in subscribed_packages):
            track_changelog(config, x)


if __name__ == '__main__':
    main()
