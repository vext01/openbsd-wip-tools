#!/usr/bin/env python

import sys
import getopt
import os.path
import shutil

# --------------------------------------------------------
# Config - XXX read from file
# --------------------------------------------------------

WIP_PATH = "/usr/ports/openbsd-wip"
MYSTUFF_PATH = "/usr/ports/mystuff"
PORTS_PATH = "/usr/ports"
ARCHIVE_PATH = "%s/.owip" % MYSTUFF_PATH

# --------------------------------------------------------
# Commands
# --------------------------------------------------------

# checks code out for work
def cmd_co(path):
    pass

def cmd_new(path):
    check_path_shape(path)

    for tree in [WIP_PATH, PORTS_PATH, MYSTUFF_PATH]: 
        if os.path.exists("%s/%s" % (tree, path)):
            print("error: path already exists in %s" % tree)
            sys.exit(1)

    # Copy in a skeleton port
    print("CREATE: %s/%s" % (MYSTUFF_PATH, path))
    os.makedirs("%s/%s" % (MYSTUFF_PATH, path))
    shutil.copyfile(
        "%s/infrastructure/templates/Makefile.template" % PORTS_PATH,
        "%s/%s/Makefile" % (MYSTUFF_PATH, path))

    # Archive away a copy for merges
    shutil.copytree("%s/%s" % (MYSTUFF_PATH, path), "%s/%s" % (ARCHIVE_PATH, path))
        
# merges code back into the tree
def cmd_ci(path):
    pass

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

