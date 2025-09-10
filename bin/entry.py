#! /usr/bin/python

import os
import sys
import re
import json

from sys import stderr

import argparse

parser = argparse.ArgumentParser(description='entry.py')

optional = parser._action_groups.pop()

requiredNamed = parser.add_argument_group('required named arguments')
#requiredNamed.add_argument("--alg", help="Algorithm directory", required=True)
#requiredNamed.add_argument("--res", help="Results directory", required=True)
#requiredNamed.add_argument("--ins", help="Instances directory", required=True)


optional.add_argument("--db", help="Variable database",
                    default=os.path.join(os.getenv("HOME"), ".variables"))
optional.add_argument("--get", nargs='+', help="Get variable")
optional.add_argument("--set", nargs=2, help="Set variable")
optional.add_argument("--clean", help="Clean variable")

parser._action_groups.append(optional)

args = parser.parse_args()

db = args.db
get = args.get
set = args.set
clean = args.clean

if (os.path.isfile(db)):
    f = open(db, "r")
    vars = json.load(f)
else:
    vars = {}

if get:
    if len(get) == 1:
        get.append('')
    sys.stdout.write(vars.get(get[0], get[1]))
elif set:
    vars[set[0]] = set[1]
    f = open(db, "w")
    json.dump(vars, f)
elif clean:
    if clean in vars:
        del vars[clean]
    f = open(db, "w")
    json.dump(vars, f)
else:
    print json.dumps(vars)
