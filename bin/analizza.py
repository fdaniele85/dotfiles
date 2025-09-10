#! /home/daniele/.venvs/scripts_1553aca88f67/bin/python3

import os
import sys
import re
import json
import argparse
import csv
import objectpath
import numpy
import random
from natsort import natsorted, ns


def round_floats(row):
    rounded_row = []
    for x in row:
        if isinstance(x, float):
            # Arrotonda a 2 decimali e formatta come stringa
            rounded_row.append(f"{x:.2f}")
        else:
            rounded_row.append(x)
    return rounded_row


parser = argparse.ArgumentParser(description='test')
parser.add_argument("--empty", help="Print rows with empty values", action="store_true")
parser.add_argument("--arguments", nargs='+', help="Arguments")
parser.add_argument("inputs", nargs='+', help="Input files")
parser.add_argument("-o", "--out", help="Output file")
parser.add_argument("--type", help="Type regex")
parser.add_argument("--replace", help="Replace")
parser.add_argument("-g", "--grep", help="Grep")
parser.add_argument("-v", help="Grep reverse", action="store_true")
parser.add_argument("--onlyOne", help="Print only one", action="store_true")
parser.add_argument("--bigType", help="Big type regex")
parser.add_argument("--stddev", help="Print std dev", action="store_true")
parser.add_argument("--median", help="Print median", action="store_true")
parser.add_argument("--mean", help="Print average", action="store_true")
parser.add_argument("--min", help="Print min", action="store_true")
parser.add_argument("--max", help="Print max", action="store_true")
parser.add_argument("--count", help="Print the count", action="store_true")
parser.add_argument("-n", "--names", nargs='+', help="Algorithms' names")
parser.add_argument("--check", help="Feasibility check")
parser.add_argument("--full", help="Full names", action="store_true")
parser.add_argument("--size", help="Check if an array has size greater than zero")

args = parser.parse_args()
inputs = [dr for dr in args.inputs if os.path.isdir(dr)]
empty = args.empty
out = args.out
richiesti = args.arguments
typeRegex = args.type
replace = args.replace
grep = args.grep
onlyOne = args.onlyOne
bigTypeReg = args.bigType
stddev = args.stddev
names = args.names
check = args.check
size = args.size
count = args.count
full = args.full

if typeRegex is None:
    typeRegex = "_\\d+\\.ris$"

if replace is None:
    replace = ""

if bigTypeReg is None:
	bigTypeReg = ".*"


v = {}
bigTypes={}
types={}
nomi = {}

if names is None:
	for dr in inputs:
		nomi[dr] = re.sub("_v?[0-9.]*$", "", dr)
else:
	for i in range(0, len(inputs)):
		nomi[inputs[i]] = names[i]



for dr in inputs:
    v[dr] = {}

    files = os.listdir(dr)
    random.shuffle(files)

    for fil in files:
        if re.search("ris$", fil):
            typ = re.sub(typeRegex, replace, fil)

            if typ not in v[dr]:
                v[dr][typ] = {}

            types[typ] = 1
            bigType = re.sub(bigTypeReg, "", fil)
            bigTypes[bigType] = 1

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

                if size is not None:
                	l = len(tree.execute('$.'+size))
                	if l <= 0:
                		continue


                for arg in richiesti:
                	try:
                		m = re.search('^(.*)\\s*\\|\\s*length$', arg)
                		if m:
                			arg = m.group(1)
                			#try:
                			x = len(tree.execute('$.'+arg))
                			#except:
                			#	x = 0
                		else:
#                			#try:
                			x = float(tree.execute('$.'+arg))
	#                		#except:
#   	             		#	x = 0

        	        	if arg not in v[dr][typ]:
        	        		v[dr][typ][arg] = []
                		v[dr][typ][arg].append(x)
                	except:
                		pass

            except ValueError:
            	pass

            except TypeError:
            	pass

            f.close()

#def sostituisci(x):
#    return re.sub("_[0-9.]*$", "", x)
#    #return x.replace("/", "")#.replace("_", "\\_")

writer = csv.writer(sys.stdout,delimiter=',')

if out:
    csvfile = open(out, 'w')
    writer = csv.writer(csvfile, delimiter=',')

trovati = list(filter(lambda x : x in v.keys(), inputs))

grandi = 0
for bigType in bigTypes:
	if not args.bigType and grandi > 0:
		break

	grandi += 1

	righe = []

	algs = trovati

	quanti = 0
	if args.mean:
		quanti += 1
	if args.median:
		quanti += 1
	if args.stddev:
		quanti += 1
	if args.count:
		quanti += 1
	if args.min:
		quanti += 1
	if args.max:
		quanti += 1

	fieldnames = ['']

	for alg in algs:
		fieldnames.append(nomi[alg])
		for i in range(0, len(richiesti)):
			if i == 0:
				end = quanti - 1
			else:
				end = quanti
			for l in range(0, end):
				fieldnames.append("")


	if not full:
		righe.append(fieldnames)
	#writer.writerow(fieldnames)

	fieldnames = ['instance']


	for alg in algs:
		for q in richiesti:
			if full:
				fieldnames.append(nomi[alg] + '.' + q)
			else:
				fieldnames.append(q)

			for l in range(0, quanti-1):
				fieldnames.append("")

	righe.append(fieldnames)

	fieldnames = ['']

	for alg in algs:
		for q in richiesti:
			if args.mean:
				fieldnames.append("Average")
			if args.median:
				fieldnames.append("Median")
			if args.stddev:
				fieldnames.append("Standard deviation")
			if args.count:
				fieldnames.append("Count")
			if args.min:
				fieldnames.append("Minimum")
			if args.max:
				fieldnames.append("Maximum")

	if quanti > 1:
		righe.append(fieldnames)

	for typ in natsorted(types, alg=ns.IGNORECASE):
		if (typ.find(bigType) == 0 or not args.bigType):
			row = []
			toPrint = False
			row.append(typ)

			for dr in trovati:
				if typ in v[dr]:

					for q in richiesti:
						m = re.search("^(.*)\\s*\\|\\s*length$", q)
						if m:
							q = m.group(1)


						#row.append(v[dr][typ][q] / div)
						if args.mean:
							if q in v[dr][typ] and len(v[dr][typ][q]) > 0:
								row.append(numpy.mean(v[dr][typ][q]))
								toPrint = True
							else:
								row.append("")
						if args.median:
							if q in v[dr][typ] and len(v[dr][typ][q]) > 0:
								row.append(numpy.median(v[dr][typ][q]))
								toPrint = True
							else:
								row.append("")
						if args.stddev:
							if q in v[dr][typ] and len(v[dr][typ][q]) > 0:
								row.append(numpy.std(v[dr][typ][q]))
								toPrint = True
							else:
								row.append("")
						if args.count:
							if q in v[dr][typ]:
								row.append(len(v[dr][typ][q]))
								toPrint = True
							else:
								row.append(0)
						if args.min:
							if q in v[dr][typ] and len(v[dr][typ][q]) > 0:
								row.append(numpy.min(v[dr][typ][q]))
								toPrint = True
							else:
								row.append("")
						if args.max:
							if q in v[dr][typ] and len(v[dr][typ][q]) > 0:
								row.append(numpy.max(v[dr][typ][q]))
								toPrint = True
							else:
								row.append("")


						
				else:
					toPrint = False
					for q in richiesti:
						if args.mean:
							row.append("")
						if args.median:
							row.append("")
						if args.stddev:
							row.append("")
						if args.min:
							row.append("")
						if args.max:
							row.append("")
						if args.count:
							row.append("")


			if empty or toPrint:
				toWrite = True
				if grep:
					if not re.search(grep, typ):
						toWrite = False

					if args.v:
						toWrite = not toWrite


				if toWrite:
					righe.append(row)
					#writer.writerow(row)
	if len(righe) > 2:
		for row in righe:
			writer.writerow(round_floats(row))
		#for i in range(0, 5):
		#	writer.writerow([])