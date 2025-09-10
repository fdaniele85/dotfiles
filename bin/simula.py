#! /usr/bin/python3

import csv
import sys
import os
import argparse

parser = argparse.ArgumentParser(description='Simula')
parser.add_argument('--target', type=int)
parser.add_argument('--tutti', type=int)
parser.add_argument('--days', type=int)
parser.add_argument('file', help="CSV file")
parser.add_argument('--pause', action="store_true", help="Pausa dopo i giorni")


args = parser.parse_args()

if not (args.target or args.days or args.tutti):
	print("At least one of --target, --days or --tutti is required")
	sys.exit(1)



giorni_passati = {}
priorita = {}
num_pr = {}
quanti = {}
iniziali = {}
rimanenti = {}

# def get_factor(pr):
# 	if pr == "Very low":
# 		return 1
# 	if pr == "Low":
# 		return 1.5
# 	if pr == "Medium":
# 		return 2
# 	if pr == "High":
# 		return 2.5
# 	if pr == "Super":
# 		return 10
# 	return 3

with open(args.file) as csv_file:
    csv_reader = csv.reader(csv_file)
    line_count = 0
    for row in csv_reader:
    	line_count += 1
    	if line_count == 1:
    		continue

    	if row[3] != "Pause" and row[7] == 'No':
    		giorni_passati[row[0]] = float(row[6])
    		iniziali[row[0]] = giorni_passati[row[0]]
    		quanti[row[0]] = 0
    		priorita[row[0]] = row[3]
    		num_pr[row[0]] = float(row[2])

def priority(serie):
	#return (giorni_passati[serie] * get_factor(priorita[serie]) + num_pr[serie], num_pr[serie])
	return giorni_passati[serie] + num_pr[serie]

if args.pause:
	os.system('clear')

i = 0
massimo = -1
minimo = -1
while True:
	if args.days and i >= args.days:
		break
	if args.target and massimo >= args.target:
		break
	if args.tutti and minimo >= args.tutti:
		break
	
	serie_max = ''
	for serie in giorni_passati.keys():
		giorni_passati[serie] += 1
	i += 1

	q = sorted([s for s in giorni_passati.keys()], key=priority, reverse=True)
	print("Giorno {}: {} {}".format(i, q[0], priority(q[0])))
	giorni_passati[q[0]] = 0
	quanti[q[0]] += 1

	if quanti[q[0]] > massimo:
		massimo = quanti[q[0]]

	minimo = min([quanti[x] for x in quanti.keys()])

if args.pause:
	input("")
os.system('clear')
print("In", i, "giorni si vedranno:")
for s in sorted(quanti.keys(), key=lambda x: quanti[x], reverse=True):
	print(quanti[s], "puntate di", s, "(priorità {}, percentuale {:.2f}%)".format(priorita[s], 100*(quanti[s]/i)))