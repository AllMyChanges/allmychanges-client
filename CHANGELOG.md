## 0.9.0 (2016-05-22)

### Major changes

* Now projects can be pushed to the server without source
URL or even name. But they will require further tuning
in HTML interface.
* Commands `push`, `tag`, `track` and `untrack` now require valid
authentication. This also means that corresponding methods
of Python API also fail without authentication.

### Fixes

* API base url scheme was changed from `http` to `https` to fix
POST requests.

### API Changes

* Function get_tags now returns iterable over all tags instead
of limited list of 10 tags.


## 0.8.0 (2016-03-26)

### Experimetal "tags" feature

This is not in AllMyChanges.com's interface yet, but
it's API now allows to tag some versions which you are
using in some projects. For that purpose, three additional
commands were added:

#### tag

This command tags given project version:

```
$ amch tag python/django 1.8.10 allmychanges.com
```

This command tells allmychanges, that I want to tag Django 1.8.10
with tag `allmychanges.com`. After this, a `tags` or `versions`
commands could provide this information.

#### tags

This command shows list of tags along with tagged projects.
Consider I runned a command from the section above. Than `tags`
output will be:

```
$ amch tags
allmychanges.com: python/django:1.8.10
```

#### versions

The other way to use information about tags is to view which versions
for the project exists:

```
$ amch versions python/django
1.10
1.9.3
1.9.2
1.9.1
1.9
1.8.10: allmychanges.com
1.8.9
1.8.8
1.8.7
1.8.6
```

Here we instantly see how stale our environments.

### Other changes

* Added option `--version`.
* Option `--config` was removed and now you have to pass token
via `--token` option or through `AMCH_TOKEN` environment variable.
* Command `export` was renamed to `pull` and it's parameter
`--output` was renamed to `--filename`.
* Command `import` was renamed to `push` and it's parameter
`--input` was renamed to `--filename`.

## 0.7.1 (2015-08-27)

* Now you can untrack packages.
Also, an example how to use this method was added.
Thanks to Alexander Sapronov, a.k.a. @WarmongeR1.

## 0.7.0 (2015-08-20)

* Added support Python 3.
* Added example how to subscribe on all packages in given namespace.

## 0.6.2 (2015-03-14)

* Fixed error which prevented new packages creation and tracking in `import` command.

## 0.6.1 (2015-02-28)

* Fixed 'import' command's issue when there is
  source field in input.

## 0.6.0 (2015-02-23)

* Improved and fixed process of adding or tracking
  packages when importing data.
* Now you can skip package instead of specifying
  its source URL, during the import.

## 0.5.1 (2015-02-18)

* Fixed data import issue when package with given
  namespace/name already exists but with different
  source. In this case we just output a warning
  and track that package. Probably in future
  this behaviour will change to asking user
  what he wants to do in this situation.

## 0.5.0 (2014-12-16)

* For case when changelog with given URL already exists
  behaviour was changed. Now a warning is displayed, and
  changelog is tracked without trying to change it's
  namespace or name.

## 0.4.0 (2014-12-16)

* Option `debug = true` now could be added to the config to make output more verbose.
* Fixed error in data import, which occur when changelog with given source
  already exists in service under different name or namespace.

## 0.3.0 (2014-11-12)

* Utility was fixed to work with newer API.

## 0.2.1 (2014-06-28)

* Commands' description was improved.

## 0.2.0 (2014-06-28)

* Added new command 'add' to add one or more packages, specifying them
  right in the command line.

## 0.1.0 (2014-06-27)

* First version of import and export commands.
