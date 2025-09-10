#! /usr/bin/env python3

import os
import sys
import re
import json
import argparse
import csv
import objectpath
import numpy


parser = argparse.ArgumentParser(description='test')
parser.add_argument("--empty", help="Print rows with empty values", action="store_true")
parser.add_argument("--arguments", nargs=2, help="Arguments")
parser.add_argument("inputs", nargs='+', help="Input files")
parser.add_argument("-o", "--out", help="Output file")
parser.add_argument("--type", help="Type regex")
parser.add_argument("--max", help="Print max", action="store_true")
parser.add_argument("--check", help="Feasibility check")
parser.add_argument("--onlyOne", help="Print only one", action="store_true")

args = parser.parse_args()
inputs = args.inputs
out = args.out
richiesti = args.arguments
typeRegex = args.type
check = args.check
onlyOne = args.onlyOne

if typeRegex is None:
    typeRegex = "_\d+\.ris$"

replace = ""


v = {}
sol = {}

for dr in inputs:
    for fil in os.listdir(dr):
        if re.search("ris$", fil):
            typ = re.sub(typeRegex, replace, fil)

            try:
                f=open(os.path.join(dr, fil))


                sys.stderr.write(os.path.join(dr, fil)+'\n')
                a = json.load(f)

                if onlyOne:
                    print(json.dumps(a, indent=2))
                    sys.exit(1)

                tree = objectpath.Tree(a)

                if check is not None:
                	if not tree.execute('$.'+check):
                		continue

                x = float(tree.execute('$.'+richiesti[0]))

                s = tree.execute('$.'+richiesti[1])

                if typ not in v:
                	v[typ] = x
                	sol[typ] = s
                elif args.max is not None:
                	if x > v[typ]:
                		v[typ] = x
                		sol[typ] = s
                elif x < v[typ]:
                	v[typ] = x
                	sol[typ] = s

            except ValueError:
            	pass

            except TypeError:
            	pass

            f.close()


writer = csv.writer(sys.stdout,delimiter=',')

if out:
    csvfile = open(out, 'w')
    writer = csv.writer(csvfile, delimiter=',')

righe = []
fieldnames = ['Instance', 'Value', 'Solution']
righe.append(fieldnames)

for typ in sorted(v.keys()):
	row = [typ, v[typ], sol[typ]]
	righe.append(row)

if len(righe) > 1:
	for row in righe:
		writer.writerow(row)
		