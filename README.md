OpenBSD-WIP-Tools
=================

This is a wrapper around cp(1) and merge(1) which allows ports hackers using
the unofficial openbsd-wip tree to work on their ports in isolation of the
rest of the git tree. This means other people's work can not interfere with
your own (unless you want it to).

Prerequisites
-------------

 * You need Python-2.7.
 * In `/usr/ports` you have a checkout of the official ports tree from CVS.
 * In `/usr/ports/openbsd-wip` you have a git checkout of the unofficial WIP
   ports tree (https://github.com/jasperla/openbsd-wip/).
 * `/usr/ports/mystuff` is your personal "sandbox" maintained by owip.py.
   You will probably want to add this to your PORTSDIRPATH in /etc/mk.conf.
   Eg. `PORTSDIR_PATH=${PORTSDIR}/mystuff:${PORTSDIR}`
 * `/usr/ports/mystuff/.owip` contains state for owip.py in the form
    of checkout-time backups of ports (so that merge(1) can work) and
    an sqlite3 database.

Workflow
--------

The basic idea is that you can work on either existing or new ports in
your own isolated sandbox (/usr/ports/mystuff) and merge the results
back into your openbsd-wip git checkout.

When you want to work on a new port, you would run:

        owip.py new <pkgpath>

Where `<pkgpath>` would be of the form `category/port`. This copys a skeleton port
into your sandbox.

When you want to work on an existing port, you would run:

        owip.py co <tree> <pkgpath>

Where `<pkgpath>` would be of the form `category/port` and `<tree>` is
either 'main' or 'wip' depending upon where the port should come from
(/usr/ports/`<pkgpath>` or /usr/ports/openbsd-wip/`<pkgpath>` respectively).

To see what you have checked out into your sandbox (and the status of
your checkouts), run:

        owip.py status

Once you want to commit your work to the openbsd-wip repo:

        owip.py ci <pkgpath>

If all went well, then you can continue to use git to add new files and
commit changes in your openbsd-wip checkout in /usr/ports/openbsd-wip.

If on the other hand a merge conflict occurs, then you will be guided through
conflict resolution. After you have manually merged conflicts, you run:

        owip.py resolved <pkgpath>

The only remaining command is the 'discard' command which discards a port
in your sandbox without merging changes back into openbsd-wip.
