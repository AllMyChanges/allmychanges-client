Command Line Client to AllMyChanges.com
=======================================

[![](https://allmychanges.com/p/python/allmychanges/badge/)](https://allmychanges.com/p/python/allmychanges/)

Installation
------------

    pip install allmychanges

Next, go to <https://allmychanges.com/account/token/> and obtain
your personal OAuth token.

Export this token as an environment variable:

    # allmychanges token
    export AMCH_TOKEN=MY-SECRET-TOKEN

Pulling package list from the service
-------------------------------------

    amch pull

Export to a number of formats is available `--help` will tell you everything.


Uploading new packages in batch mode
---------------------------------

Prepare a datafile in one of supported formats and run

    amch push --format yaml --input data.yaml

If you didn't entered sources for some packages, script
will ask you where these sources are. Answer honestly. :)

In some cases, script will try to help you. If somebody
already added package with such name and namespace, it will
suggest you the source. For python and perl packages, it will
search different urls on the PyPi's pages or metacpan.org
respectively.

This command also accepts `--tag <some-tag>` argument, and
every uploaded package will be tagged with this tag, if there
is a `version` column in the data.


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
```
pip install pip2amch allmychanges
export AMCH_TOKEN=<your token>
    
pip2amch --tag myproject requirements.txt | amch push
```
Utility `pip2amch` generates CSV data, for `amch push`.

Roadmap
-------

* Write npm2amch, similar to pip2amch
* May be write something like that for ruby.

Hacking
-------

Feel free [to fork](https://github.com/svetlyak40wt/allmychanges), file issues and send me patches.
