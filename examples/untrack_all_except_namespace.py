# -*- encoding: utf-8 -*-
from allmychanges.api import get_changelogs, untrack_changelog
from allmychanges.config import read_config


def main():
    config = read_config()
    section = 'python'

    changelogs = get_changelogs(config, tracked=True)

    all_cnt = len(changelogs)
    for i, x in enumerate(reversed(changelogs)):
        if i % 10 == 0:
            print("Process: %s of %s" % (i, all_cnt))
        if x['namespace'] != section:
            untrack_changelog(config, x)


if __name__ == '__main__':
    main()
