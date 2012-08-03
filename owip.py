#!/usr/bin/env python

import sys
import getopt
import os.path
import shutil
import subprocess

# --------------------------------------------------------
# Various globals
# --------------------------------------------------------

# paths
WIP_PATH = "/usr/ports/openbsd-wip"
MYSTUFF_PATH = "/usr/ports/mystuff"
PORTS_PATH = "/usr/ports"
ARCHIVE_PATH = os.path.join(MYSTUFF_PATH, ".owip")

# bsd merge
MERGE = "/usr/bin/merge"

# merge return codes
MERGE_OK = 0
MERGE_CONFLICT = 1
MERGE_ERROR = 2

# --------------------------------------------------------
# Commands
# --------------------------------------------------------

# checks code out for work
def cmd_co(path):
    pass

def cmd_new(path):
    check_path_shape(path)

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
        
# merges code back into the tree
def cmd_ci(path):

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
def cmd_trash(path):
    pass

def cmd_status(path):
    pass

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

def scaffold_dirs():
    if not os.path.exists(MYSTUFF_PATH):
        os.mkdir(MYSTUFF_PATH)

    if not os.path.exists(ARCHIVE_PATH):
        os.mkdir(ARCHIVE_PATH)

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

    scaffold_dirs()

    # dispatch
    tup[0](*sys.argv[2:])

