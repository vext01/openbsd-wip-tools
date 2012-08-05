#!/usr/bin/env python

import sys
import getopt
import os.path
import shutil
import subprocess
import sqlite3

# --------------------------------------------------------
# Various globals
# --------------------------------------------------------

# paths
WIP_PATH = "/usr/ports/openbsd-wip"
MYSTUFF_PATH = "/usr/ports/mystuff"
PORTS_PATH = "/usr/ports"
ARCHIVE_PATH = os.path.join(MYSTUFF_PATH, ".owip")
DB_PATH = os.path.join(MYSTUFF_PATH, ".owip", "sandbox.db")

# bsd merge
MERGE = "/usr/bin/merge"

# merge return codes
MERGE_OK = 0
MERGE_CONFLICT = 1
MERGE_ERROR = 2

ORIGIN_NEW = 0
ORIGIN_WIP = 1
ORIGIN_PORTS = 2 # as in official CVS

# Status flags (more later perhaps)
STATUS_CONFLICT = 1 << 0

# --------------------------------------------------------
# Commands
# --------------------------------------------------------

# checks code out for work
def cmd_co(db, path):
    pass

def cmd_new(db, path):
    check_path_shape(path)
    curs = db.cursor()

    # sanity checks
    curs.execute("SELECT * FROM checkout WHERE pkgpath = ?", (path, ))
    if len(curs.fetchall()) != 0:
        print("error: already checked out in %s" % \
            os.path.join(MYSTUFF_PATH, path))
        sys.exit(1)

    for tree in [WIP_PATH, PORTS_PATH, MYSTUFF_PATH]: 
        if os.path.exists(os.path.join(tree, path)):
            print("error: path already exists in %s" % tree)
            sys.exit(1)

    # Copy in a skeleton port
    os.makedirs(os.path.join(MYSTUFF_PATH, path))
    shutil.copyfile(
        os.path.join(PORTS_PATH, "infrastructure", "templates", "Makefile.template"),
        os.path.join(MYSTUFF_PATH, path, "Makefile"))

    # Archive away a copy for merges
    shutil.copytree(os.path.join(MYSTUFF_PATH, path), os.path.join(ARCHIVE_PATH, path))

    # Update db
    curs.execute("INSERT INTO checkout (pkgpath, origin, flags) VALUES " + \
        "(?, ?, ?)", (path, ORIGIN_NEW, 0))
    db.commit()

    print("New port checked out into %s" % (os.path.join(MYSTUFF_PATH, path)))

# merges code back into the tree
def cmd_ci(db, path):

    # sanity checks
    for tree in [MYSTUFF_PATH, ARCHIVE_PATH]:
        if not os.path.exists(os.path.join(tree, path)):
            print("error: can't find checkout in %s" % tree)
            sys.exit(1)


    check_path_shape(path)

    for dirname, dirnames, filenames in os.walk(os.path.join(MYSTUFF_PATH, path)):
        for fn in filenames:

            mystuff_path = os.path.join(dirname, fn)
            wip_path = mystuff_path.replace(MYSTUFF_PATH, WIP_PATH)
            archive_path = mystuff_path.replace(MYSTUFF_PATH, ARCHIVE_PATH)

            # incase of a new checkin, scaffold dirs
            if not os.path.exists(os.path.dirname(wip_path)):
               os.mkdir(os.path.dirname(wip_path))

            # if the file exists, we merge
            if os.path.exists(wip_path):
                sys.stdout.write("Merging '%s'..." % mystuff_path)

                print("I would run: %s" % ("%s %s %s %s" % (MERGE, wip_path, archive_path, mystuff_path)))
                status = subprocess.call([MERGE, wip_path, archive_path, mystuff_path])

                if status == MERGE_OK:
                    print("OK")
                elif status == MERGE_CONFLICT:
                    print("\nThere was a merge conflict!")

                    print("Hit enter to resolve this by hand")
                    raw_input()

                    EDITOR = os.getenv("EDITOR")
                    if EDITOR is None:
                        EDITOR = "/usr/bin/vi"

                    status = subprocess.call([EDITOR, wip_path])
                    if status != 0:
                        print("error: failed to invoke editor, merge it yourself ;)")
                        sys.exit(1)

                else:
                    print("error: Merge failed: merge returned: %d" % status)
                    sys.exit(1)
            else:
                print("Copying in new file '%s'" % mystuff_path)
                shutil.copyfile(mystuff_path, wip_path)

# discards work in your sandbox
def cmd_trash(db, path):
    pass

def cmd_status(db):
    curs = db.cursor()

    curs.execute("SELECT * FROM checkout")
    rows = curs.fetchall()

    for r in rows:
        print("%s\n    origin: %s\n    flags: %s" % \
            (r[0], get_origin_str(r[1]), get_status_str(r[2])))

owip_cmds = {
        # command name  (function,  n_args, help)
        "co" :      (cmd_co,    1,  "checks code out into your sandbox"),
        "ci" :      (cmd_ci,    1,  "merges code back into openbsd-wip"),
        "trash" :   (cmd_trash, 1,  "discards work in your sandbox"),
        "status" :  (cmd_status,0,  "show what you have checked out etc."),
        "new" :     (cmd_new,   1,  "start work on a new port"),
        }

# --------------------------------------------------------
# The rest
# --------------------------------------------------------


def get_origin_str(ocode):
    if ocode == ORIGIN_NEW:
        return "new port"
    elif ocode == ORIGIN_WIP:
        return MYSTUFF_PATH
    elif ocode == ORIGIN_PORTS:
        return PORTS_PATH

    print("error: unknown origin: %d" % ocode)
    sys.exit(1)

def get_status_str(flags):
    fstr = ""

    if (flags & STATUS_CONFLICT):
        fstr += "CONFLICT"

    return fstr


def usage():
    print("Usage: owip.py cmd <args>")
    for (cmd, tup) in owip_cmds.items():
        print("    %s: %s" % (cmd.ljust(10), tup[2]))

def check_path_shape(path):
    # XXX strip dots or complain
    err = False

    if "/" not in path:
        err = True
    else:
        elems = path.split("/")
        if len(elems) != 2:
            err = True

    if err:
        print("error: Malformed ports path.")
        print("    Paths should be of the form 'category/dir'")
        sys.exit(1)

def connect_db():
    if not os.path.exists(MYSTUFF_PATH):
        os.mkdir(MYSTUFF_PATH)

    if not os.path.exists(ARCHIVE_PATH):
        os.mkdir(ARCHIVE_PATH)

    db = sqlite3.connect(DB_PATH)
    curs = db.cursor()

    curs.execute("CREATE TABLE IF NOT EXISTS checkout (" + \
        "pkgpath STRING PRIMAMRY KEY, " + \
        "origin INT, " + \
        "flags INT)")

    return db

# --------------------------------------------------------
# Main
# --------------------------------------------------------

if __name__ == "__main__":

    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    # lookup requested command
    for (cmd, tup) in owip_cmds.items():
        if cmd == sys.argv[1] and tup[1] == len(sys.argv) - 2:
            break
    else:
        # invalid command
        print("error: unknown command")
        usage()
        sys.exit(1)

    db = connect_db()

    # dispatch
    args = [db]
    args.extend(sys.argv[2:])
    tup[0](*args)
