#! /usr/bin/python

import os
import sys
import re
import json
import argparse
import csv
import random


parser = argparse.ArgumentParser(description='test')
parser.add_argument("inputs", nargs='+', help="Input files")
parser.add_argument("-o", "--out", help="Output file")
parser.add_argument("--type", help="Type regex")
parser.add_argument("--minmax", help="Type regex", default="max")

args = parser.parse_args()
inputs = args.inputs
out = args.out
typeRegex = args.type
minmax = args.minmax

if typeRegex is None:
    typeRegex = "_\d+\.ris$"


maximum = {}
minimum = {}
js = {}
instances = {}
maxtime = 0

tutti = {}
files = set({})

for dr in inputs:
	js[dr] = {}
	instances[dr] = set({})
	tutti[dr] = {}

	for fil in os.listdir(dr):
		sys.stderr.write(fil+'\n')
		if re.search("ris$", fil):
			typ = re.sub(typeRegex, '', fil)

			try:
				#print os.path.join(dr, fil)
				f=open(os.path.join(dr, fil))

				a = json.load(f)

				tutti[dr][fil] = a
				files.add(fil)
			except ValueError, e:
				pass
			f.close()

beccati = set({})

for fil in files:
	inTutti = True
	for dr in tutti.keys():
		if fil not in tutti[dr]:
			inTutti = False
			break

	if inTutti:
		beccati.add(fil)

for dr in inputs:
	for fil in beccati:
		typ = re.sub(typeRegex, '', fil)

		try:
			sys.stderr.write(dr+"/"+fil+'\n')
			a = tutti[dr][fil]

			if (typ not in maximum) or a['Solution']['Cost'] > maximum[typ]:
					maximum[typ] = a['Solution']['Cost']

			if (typ not in minimum) or a['Solution']['Cost'] < minimum[typ]:
					minimum[typ] = a['Solution']['Cost']
					

			if a['Algorithm']['Time']['wall'] > maxtime:
				maxtime = a['Algorithm']['Time']['wall']

			js[dr][typ] = js[dr].get(typ, []) + [a]
			instances[dr].add(typ)

		except ValueError, e:
			pass

		f.close()

writer = csv.writer(sys.stdout,delimiter=',')

if out:
    csvfile = open(out, 'w')
    writer = csv.writer(csvfile, delimiter=',')

writer.writerow(["Algorithm", "Tau", "Probability"])
for dr in inputs:
	p = []
	for k in range(0, int(maxtime+1), int(maxtime / 100)):

		quanti = 0.0

		for fil in beccati:
			typ = re.sub(typeRegex, '', fil)
			a = tutti[dr][fil]

			sys.stderr.write('last: ' +dr+'/'+fil+'\n')

			for q in a['Algorithm']['Incumbents']:

				tofind = maximum[typ]
				if minmax == "min":
					tofind = minimum[typ]
				elif minmax == "med":
					tofind = (minimum[typ] + maximum[typ]) / 2

				if q['Time']['wall'] <= k:
					if q['Cost']['Feasible'] and q['Cost']['Cost'] <= tofind:
						quanti += 1
						break

		writer.writerow([dr, k, quanti / len(beccati)])

