Command Line Client to AllMyChanges.com
=======================================

[![](https://allmychanges.com/p/python/allmychanges/badge/)](https://allmychanges.com/p/python/allmychanges/)

Installation
------------

    pip install allmychanges

Next, go to <https://allmychanges.com/account/token/> and obtain
your personal OAuth token.

Write this token into the config file like that:

    # allmychanges.cfg
    [allmychanges]
    token = MY-SECRET-TOKEN

Exporting package list
----------------------

    amch export

Export to a number of formats is available `--help` will tell you everything.


Adding new packages in batch mode
---------------------------------

Prepare a datafile in one of supported formats and run

    amch import --format yaml --input data.yaml

If you didn't entered sources for some packages, script
will ask you where these sources are. Answer honestly. :)

In some cases, script will try to help you. If somebody
already added package with such name and namespace, it will
suggest you the source. For python and perl packages, it will
search different urls on the PyPi's pages or metacpan.org
respectively.


Adding one or few packages from command line
--------------------------------------------

This is also very easy:

    amch add python/clint python/requests perl/Dancer

You could also specify a source url, like that:

    amch add python/Dancer/https://github.com/PerlDancer/Dancer

But if you didn't, service will try to figure out url automatically
and will suggest it in same way as it does in `import` command.

Using amch to import requirements.txt
-------------------------------------

### On Linux
    cat requirements.txt | grep -v '^-e' | sed -e 's/\([^=]\+\).*/python,\1/' -e '1 i\namespace,name' > data
    amch import --input data

### On OSX

OSX have a posix `sed` command which is more strict and don't allow to do what we want in one line. The easiest way to overcome this, is to install `gnu-sed` via brew and to use `gsed` instead of `sed`: 

    brew install gnu-sed
    cat requirements.txt | grep -v '^-e' | gsed -e 's/\([^=]\+\).*/python,\1/' -e '1 i\namespace,name' > data
    amch import --input data

Roadmap
-------

* Process pip's requirements.txt files.
* May be process some requirements of ruby and npm packages too.

Hacking
-------

Feel free [to fork](https://github.com/svetlyak40wt/allmychanges), file issues and send me patches.
