#! /home/daniele/.venvs/scripts_1553aca88f67/bin/python3

import os
import sys
import re
import json
import argparse
import csv
import random
import tempfile
import subprocess


parser = argparse.ArgumentParser(description='test')
parser.add_argument("inputs", nargs='+', help="Input files")
parser.add_argument("-o", "--out", help="Output file", required=True)
parser.add_argument("-a", "--ask", help="Ask for algorithms", action='store_true')
parser.add_argument("--type", help="Type regex")
parser.add_argument("-M", help="Type regex", required=True)
parser.add_argument("--minmax", help="Type regex", default="max")
parser.add_argument("-g", "--grep", help="Grep regex")
parser.add_argument("-n", "--names", nargs='+', help="Algorithms' names")
parser.add_argument(
	"--sense",
	choices=("min", "max"),
	default="min",
	help="Optimization sense (default: min)",
)
parser.add_argument(
	"--cost-path",
	default="solution.cost",
	help="Dot-separated JSON path of the final solution cost (default: solution.cost)",
)
parser.add_argument(
	"--incumbent-cost-path",
	default="cost",
	help="Dot-separated cost path relative to each incumbent (default: cost)",
)

args = parser.parse_args()
inputs = args.inputs
out = args.out
typeRegex = args.type
M = int(args.M)
minmax = args.minmax
grep = args.grep
ask = args.ask
names = args.names
maximize = args.sense == "max"
costPath = args.cost_path
incumbentCostPath = args.incumbent_cost_path


def json_value(value, path):
	"""Return the value at a dot-separated path in a JSON object."""
	for element in path.split('.'):
		if isinstance(value, list):
			value = value[int(element)]
		else:
			value = value[element]
	return value


def normalized_cost(value, path):
	"""Map both optimization senses to minimization."""
	cost = json_value(value, path)
	return -cost if maximize else cost


def displayed_cost(cost):
	return -cost if maximize else cost

if typeRegex is None:
    typeRegex = "_\\d+\\.ris$"

algs={}
if ask:
	for dr in inputs:
		alg = raw_input("Nome di " + dr+ ": ")
		algs[dr] = alg
elif not names is None:
	for i in range(0, len(inputs)):
		algs[inputs[i]] = names[i]
else:
	for dr in inputs:
		algs[dr] = dr

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
		if re.search("ris$", fil):
			typ = re.sub(typeRegex, '', fil)

			try:
				#print os.path.join(dr, fil)
				f=open(os.path.join(dr, fil))

				a = json.load(f)

				tutti[dr][fil] = a
				files.add(fil)
			except:
				pass
			f.close()

beccati = set({})

for fil in files:
	inTutti = True
	if not grep is None:
		if not re.search(grep, fil):
			inTutti = False

	for dr in tutti.keys():
		if fil not in tutti[dr]:
			inTutti = False
			break

	if inTutti:
		beccati.add(fil)

for fil in beccati:
	sys.stderr.write("Beccato " + fil+'\n')


minimum = {}
for dr in inputs:
	minimum[dr] = {}
	for fil in beccati:
		typ = re.sub(typeRegex, '', fil)
		a = tutti[dr][fil]

		cost = normalized_cost(a, costPath)
		if (typ not in minimum[dr]) or cost < minimum[dr][typ]:
			minimum[dr][typ] = cost

if minmax == 'worst':
	for dr in inputs:
		for fil in beccati:
			typ = re.sub(typeRegex, '', fil)
			a = tutti[dr][fil]
			cost = normalized_cost(a, costPath)
			if (typ not in maximum) or maximum[typ] < cost:
				maximum[typ] = cost
else:
	for dr in inputs:
		for typ in minimum[dr].keys():
			if (typ not in maximum) or minimum[dr][typ] > maximum[typ]:
				maximum[typ] = minimum[dr][typ]

for typ in maximum.keys():
	print(typ, displayed_cost(maximum[typ]))

minimum = {}
for dr in inputs:
	for fil in beccati:
		typ = re.sub(typeRegex, '', fil)

		try:
			sys.stderr.write(dr+"/"+fil+'\n')
			a = tutti[dr][fil]

			#if (typ not in maximum) or a['Solution']['Cost'] > maximum[typ]:
			#		maximum[typ] = a['Solution']['Cost']

			cost = normalized_cost(a, costPath)
			if (typ not in minimum) or cost < minimum[typ]:
					minimum[typ] = cost
					

			if a['time']['wall'] > maxtime:
				maxtime = a['time']['wall']

			js[dr][typ] = js[dr].get(typ, []) + [a]
			instances[dr].add(typ)

		except:
			pass

		f.close()

[fp, tmpfilename] = tempfile.mkstemp(suffix='.csv')
os.close(fp)
fp = open(tmpfilename, 'w')
writer = csv.writer(fp,delimiter=',')

#writer = csv.writer(sys.stdout,delimiter=',')

#if out:
#    csvfile = open(out, 'w')
#    writer = csv.writer(csvfile, delimiter=',')

writer.writerow(["Algorithm", "Time", "Probability"])
for dr in inputs:
	sar = []
	for k in range(0, M):
		s = 0.0

		for typ in instances[dr]:
			a = random.choice(js[dr][typ])

			tofind = maximum[typ]
			if minmax == "min":
				tofind = minimum[typ]
			elif minmax == "med":
				tofind = (minimum[typ] + maximum[typ]) / 2

			tofind += 0.01

			# sys.stderr.write("Per " + typ + " bisogna trovare " + str(tofind) + "\n")

			found = False
			toadd = 0

			if len(a['incumbents']) > 0:
				for q in a['incumbents']:
					# sys.stderr.write(dr + ":" + typ + ":"+ str(q['Cost']['Cost']) +":" + str(tofind) + "\n")
					if normalized_cost(q, incumbentCostPath) <= tofind:
						toadd = q['time']
						found = True
						break
			else:
				if a['solution']['feasible'] and normalized_cost(a, costPath) <= tofind:
					toadd = a['time']['wall']
					found = True



			if not found:
				toadd = maxtime
			
			s+= toadd
			# sys.stderr.write("Per " + dr + " su " + typ + " aggiungo " + str(toadd) + "\n")

		sar.append(s)

	sar.sort()
	p = []
	for k in range(0, M):
		row = [algs[dr],sar[k],(0.5+k)/M]
		writer.writerow(row)

fp.close()

print(tmpfilename, out)
subprocess.call (["/usr/bin/Rscript", "--vanilla", "/home/daniele/mttt.r", "--infile", tmpfilename, "--out" , out])
