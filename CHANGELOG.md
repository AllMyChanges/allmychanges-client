0.7.1 (2015-08-27)
==================

* Now you can untrack packages.
Also, an example how to use this method was added.
Thanks to Alexander Sapronov, a.k.a. @WarmongeR1.

0.7.0 (2015-08-20)
==================

* Added support Python 3.
* Added example how to subscribe on all packages in given namespace.

0.6.2 (2015-03-14)
==================

* Fixed error which prevented new packages creation and tracking in `import` command.

0.6.1 (2015-02-28)
==================

* Fixed 'import' command's issue when there is
  source field in input.

0.6.0 (2015-02-23)
==================

* Improved and fixed process of adding or tracking
  packages when importing data.
* Now you can skip package instead of specifying
  its source URL, during the import.

0.5.1 (2015-02-18)
==================

* Fixed data import issue when package with given
  namespace/name already exists but with different
  source. In this case we just output a warning
  and track that package. Probably in future
  this behaviour will change to asking user
  what he wants to do in this situation.

0.5.0 (2014-12-16)
==================

* For case when changelog with given URL already exists
  behaviour was changed. Now a warning is displayed, and
  changelog is tracked without trying to change it's
  namespace or name.

0.4.0 (2014-12-16)
==================

* Option `debug = true` now could be added to the config to make output more verbose.
* Fixed error in data import, which occur when changelog with given source
  already exists in service under different name or namespace.

0.3.0 (2014-11-12)
==================

* Utility was fixed to work with newer API.

0.2.1 (2014-06-28)
==================

* Commands' description was improved.

0.2.0 (2014-06-28)
==================

* Added new command 'add' to add one or more packages, specifying them
  right in the command line.

0.1.0 (2014-06-27)
==================

* First version of import and export commands.
