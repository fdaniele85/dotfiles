#! /usr/bin/python

import os
import sys
import re
import json
import argparse
import csv
import objectpath


parser = argparse.ArgumentParser(description='test')
parser.add_argument("--arguments", nargs='+', help="Arguments")
parser.add_argument("inputs", nargs='+', help="Input files")
parser.add_argument("-o", "--out", help="Output file")
parser.add_argument("--type", help="Type regex")
parser.add_argument("--replace", help="Replace")
parser.add_argument("-g", "--grep", help="Grep")
parser.add_argument("-v", help="Grep reverse", action="store_true")
parser.add_argument("--onlyOne", help="Print only one", action="store_true")
parser.add_argument("--bigType", help="Big type regex")
parser.add_argument("--melt", help="Melt the table", action="store_true")
parser.add_argument("--stddev", help="Print std dev", action="store_true")
parser.add_argument("-n", "--names", nargs='+', help="Algorithms' names")

args = parser.parse_args()
inputs = args.inputs
out = args.out
richiesti = args.arguments
typeRegex = args.type
replace = args.replace
grep = args.grep
onlyOne = args.onlyOne
bigTypeReg = args.bigType
melt = args.melt
stddev = args.stddev
names = args.names

if typeRegex is None:
    typeRegex = "_\d+\.ris$"

if replace is None:
    replace = ""

if bigTypeReg is None:
	bigTypeReg = ".*"


types = {}
all_files = {}
table = {}
nomi = {}

if names is None:
	for dr in inputs:
		nomi[dr] = re.sub("_[0-9.]*$", "", dr)
else:
	for i in range(0, len(inputs)):
		nomi[inputs[i]] = names[i]


for arg in richiesti:
	for dr in inputs:
		nome = nomi[dr]
		table[nome+'.'+arg] = {}


for dr in inputs:
	nome = nomi[dr]

	for fil in os.listdir(dr):
		if re.search("ris$", fil):
			typ = re.sub(typeRegex, replace, fil)

			types[fil] = typ
			all_files[fil] = 1

			try:
				f=open(os.path.join(dr, fil))

				sys.stderr.write(os.path.join(dr, fil)+'\n')
				a = json.load(f)

				if onlyOne:
					print json.dumps(a, indent=2)
					sys.exit(1)

				tree = objectpath.Tree(a)

				for arg in richiesti:
					try:
						x = tree.execute('$.'+arg)
					except:
						x = ''
					table[nome+'.'+arg][fil] = x

			except ValueError, e:
				pass


			f.close()

writer = csv.writer(sys.stdout,delimiter=',')

if out:
    csvfile = open(out, 'w')
    writer = csv.writer(csvfile, delimiter=',')

riga = ['type','file']
for dr in inputs:
	nome = nomi[dr]
	for arg in richiesti:
		riga.append(nome+'.'+arg)

writer.writerow(riga)

for fil in sorted(all_files):
	riga = [types[fil], fil]
	for dr in inputs:
		nome = nomi[dr]

		for arg in richiesti:
			x = table[nome+'.'+arg].get(fil, '')
			riga.append(x)
	writer.writerow(riga)