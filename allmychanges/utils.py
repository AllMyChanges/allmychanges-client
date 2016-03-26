# coding: utf-8


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
