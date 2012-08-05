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

# shell utils
MERGE = "/usr/bin/merge"
GIT = "/usr/local/bin/git"

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
def cmd_co(db, tree_name, path):
    check_path_shape(path)
    curs = db.cursor()

    # sanity checks
    curs.execute("SELECT * FROM checkout WHERE pkgpath = ?", (path, ))
    if len(curs.fetchall()) != 0:
        print("Error: Already checked out in %s" % \
            os.path.join(MYSTUFF_PATH, path))
        exit_nicely(db)

    if tree_name == "wip":
        tree = WIP_PATH
        origin = ORIGIN_WIP
    elif tree_name ==  "main":
        tree = PORTS_PATH
        origin = ORIGIN_PORTS
    else:
        print("Error: Bad tree path. Should be either 'wip' or 'main'")
        exit_nicely(db)

    if os.path.exists(os.path.join(MYSTUFF_PATH, path)):
        print("error: Destination path exists: %s" % \
            os.path.join(MYSTUFF_PATH, path))
        exit_nicely(db)

    if not os.path.exists(os.path.join(tree, path)):
        print("error: Source path does not exist: %s" % \
            os.path.join(tree, path))
        exit_nicely(db)

    # We might have to create the category directory
    category_dir = os.path.dirname(os.path.join(MYSTUFF_PATH, path))
    if not os.path.exists(category_dir):
        os.mkdir(category_dir)

    # Copy in from source
    shutil.copytree( \
        os.path.join(tree, path), os.path.join(MYSTUFF_PATH, path), \
        ignore=shutil.ignore_patterns("CVS"))

    # Archive away a copy for merges
    shutil.copytree(os.path.join(tree, path), os.path.join(ARCHIVE_PATH, path), \
        ignore=shutil.ignore_patterns("CVS"))

    # Update db
    curs.execute("INSERT INTO checkout (pkgpath, origin, flags) VALUES " + \
        "(?, ?, ?)", (path, origin, 0))
    db.commit()

    print("Port checked out into %s" % (os.path.join(MYSTUFF_PATH, path)))

def cmd_new(db, path):
    check_path_shape(path)
    curs = db.cursor()

    # sanity checks
    curs.execute("SELECT * FROM checkout WHERE pkgpath = ?", (path, ))
    if len(curs.fetchall()) != 0:
        print("Error: Already checked out in %s" % \
            os.path.join(MYSTUFF_PATH, path))
        exit_nicely(db)

    for tree in [WIP_PATH, PORTS_PATH, MYSTUFF_PATH]: 
        if os.path.exists(os.path.join(tree, path)):
            print("Error: Path already exists in %s" % tree)
            exit_nicely(db)

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
    check_path_shape(path)
    curs = db.cursor()

    # sanity checks
    curs.execute("SELECT * FROM checkout WHERE pkgpath = ?", (path, ))
    rows = curs.fetchall()
    if len(rows) != 1:
        print("Error: Not checked out" % \
            os.path.join(MYSTUFF_PATH, path))
        exit_nicely(db)

    if rows[0][2] == STATUS_CONFLICT:
        print("Error: This path is in conflict. merge manually (in %s) and use " + \
            "'owip.py resolved %s'" % (path, os.path.join(WIP_PATH, path)))
        exit_nicely(db)

    for tree in [MYSTUFF_PATH, ARCHIVE_PATH]:
        if not os.path.exists(os.path.join(tree, path)):
            print("Error: Can't find checkout in %s" % tree)
            exit_nicely(db)

    status = 0
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
                merge_print = mystuff_path.replace(MYSTUFF_PATH, "")
                sys.stdout.write("merging '%s'..." % merge_print)

                merge_st = subprocess.call( \
                    [MERGE, wip_path, archive_path, mystuff_path])

                if merge_st == MERGE_OK:
                    print(" [ OK ]")
                elif merge_st == MERGE_CONFLICT:
                    print("[ FAIL ]")
                    status = status | STATUS_CONFLICT

                    print("Error: There was a merge conflict!")
                    print("       Hit enter to resolve this by hand...")
                    raw_input()

                    EDITOR = os.getenv("EDITOR")
                    if EDITOR is None:
                        EDITOR = "/usr/bin/vi"

                    ed_stat = subprocess.call([EDITOR, wip_path])
                    if ed_stat != 0:
                        print("Error: Failed to invoke editor, merge it yourself ;)")
                        exit_nicely(db)
                else:
                    print("Error: Merge failed: merge returned: %d" % status)
                    print("     : This sould not happen, thus your sandbox state is inconsistent")
                    exit_nicely(db)
            else:
                print("Copying in new file '%s'" % mystuff_path)
                shutil.copyfile(mystuff_path, wip_path)

    if status & STATUS_CONFLICT != 0:
        curs.execute("UPDATE checkout SET flags = ? WHERE pkgpath = ?", \
            (status, path))
        db.commit()
        print("Warning: Merge conflicts occurred!")
        print("       : If you were able to resolve these, " + \
            "run 'owip.py resolved %s'." % path)
        print("       : Your sandbox is untouched")
    else:
        clear_checkout(db, path)
        print("Checkin was successful!")
        print("Now go to %s and use git to commit your work to openbsd-wip" % \
            os.path.join(WIP_PATH, path))

def clear_checkout(db, path):
    check_path_shape(path)

    for tree in [MYSTUFF_PATH, ARCHIVE_PATH]:
        category = os.path.join(tree, os.path.dirname(path))
        shutil.rmtree(os.path.join(tree, path))

        # if this was the last port in category, rm category dir too
        if len(os.listdir(category)) == 0:
            os.rmdir(category)

    db.cursor().execute("DELETE FROM checkout WHERE pkgpath = ?", (path, ))
    db.commit()

# informs owip that you manually resolved a merge conflict
def cmd_resolved(db, path):
    check_path_shape(path)
    curs = db.cursor()

    # sanity
    curs.execute("SELECT * FROM checkout WHERE pkgpath = ?", (path, ))
    rows = curs.fetchall()
    if len(rows) != 1:
        print("Error: Not checked out")
        exit_nicely(db)

    if rows[0][2] & STATUS_CONFLICT == 0:
        print("Error: %s is not in conflict state" % path)
        exit_nicely(db)

    clear_checkout(db, path)

    print("Conflict cleared. Now go to %s and use git to commit your work to openbsd-wip" % \
        os.path.join(WIP_PATH, path))

# discards work in your sandbox
def cmd_discard(db, path):
    check_path_shape(path)
    curs = db.cursor()

    # sanity
    curs.execute("SELECT * FROM checkout WHERE pkgpath = ?", (path, ))
    rows = curs.fetchall()
    if len(rows) != 1:
        print("Error: Not checked out")
        exit_nicely(db)

    if rows[0][2] & STATUS_CONFLICT != 0:
        print("Error: %s is in conflict state" % path)
        exit_nicely(db)

    clear_checkout(db, path)
    print("Discarded %s" % path)

def cmd_status(db):
    curs = db.cursor()

    curs.execute("SELECT * FROM checkout")
    rows = curs.fetchall()

    for r in rows:
        print("%s\n    origin: %s\n    flags: %s" % \
            (r[0], get_origin_str(r[1]), get_status_str(r[2])))

owip_cmds = {
        # command name  (function,  n_args, help)
        "co" :      (cmd_co,      2, "<tree> <pkgpath>. Checks out from <tree> into your sandbox"),
        "ci" :      (cmd_ci,      1, "<pkgpath>. Merges code back into openbsd-wip"),
        "discard" : (cmd_discard, 1, "<pkgpath>. Discards work in your sandbox"),
        "new" :     (cmd_new,     1, "<pkgpath>. Start work on a new port"),
        "status" :  (cmd_status,  0, "Show what you have checked out etc."),
        "resolved" :(cmd_resolved,1, "<pkgpath>. Marks a conflict resolved"),
        }

# --------------------------------------------------------
# The rest
# --------------------------------------------------------


def get_origin_str(ocode):
    if ocode == ORIGIN_NEW:
        return "new port"
    elif ocode == ORIGIN_WIP:
        return "openbsd-ports-wip"
    elif ocode == ORIGIN_PORTS:
        return "official ports tree"

    print("error: unknown origin: %d" % ocode)
    exit_nicely(db)

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
        exit_nicely(db)

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

def exit_nicely(db):
    db.close()
    sys.exit(1)

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

    db.close()
