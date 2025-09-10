#! /usr/bin/python3

import argparse
import csv
import sys
import os
import numpy as np


parser = argparse.ArgumentParser(description='test')
parser.add_argument("file", help="Input files")
parser.add_argument("-r", "--rows", help="Rows to skip")
parser.add_argument("-c", "--columns", help="Columns to skip")
parser.add_argument("-p", "--percentage", help="Percentage")

args = parser.parse_args()
file = args.file
nRows = args.rows
nCols = args.columns
p = 0
if not args.percentage is None:
	p = int(args.percentage)

if nRows is None:
	nRows = 2
else:
	nRows = int(nRows)

if nCols is None:
	nCols = 1
else:
	nCols = int(nCols)

def average_column (rows, nr, nc):

	column_totals = []
	row_count = 0.0

	for row in rows:

		if len(row) == 0:
			continue

		row_count += 1
		if row_count == 1:
			i = 0
			for value in row:
				column_totals.append([])
				i+=1

		if row_count <= nr:
			continue

		i = 0

		for value in row:
			if i < nc:
				i += 1
				continue

			if value != '':
				n = float(value)
				column_totals[i].append(n)

			i += 1




	# row_count is now 1 too many so decrement it back down
	row_count -= nr

	# calculate per column averages using a list comprehension
	averages = [np.mean(column_totals[idx]) for idx in range(nc, len(column_totals))]
	averages = [f"{x:.2f}" for x in averages]
	if nc > 0:
		averages = ["Average"] + averages
	return averages


if file == '-':
	f = sys.stdin
	q = sys.stdout
else:
	f = open(file,"r")
	q = open(file+".out", "w")

reader = csv.reader(f)
rows = [row for row in reader]

averages = average_column(rows, nRows, nCols)

writer = csv.writer(q,delimiter=',')


for row in rows:
	if len(row) > 0:
		writer.writerow(row)


writer.writerow(averages)
if p > 0:
	row=[''] * nCols


	for j in range(0, p):
		row.append('')

	rep = (len(averages)-nCols)/p

	for q in range(1, rep):
		for j in range(0, p):
			row.append(averages[nCols + p*q + j] / averages[nCols + j] - 1)
	writer.writerow(row)

if file != '-':
	os.rename(file, file+".bak")
	os.rename(file+".out", file)