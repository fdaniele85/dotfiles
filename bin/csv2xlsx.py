#! /home/daniele/.venvs/scripts_1553aca88f67/bin/python3

import pandas as pd
import sys
import os
import csv

import argparse

parser = argparse.ArgumentParser(description='csv2xlsx.py')

parser.add_argument('-o', "--output", help="Output file", required=True)
parser.add_argument("inputs", nargs='+', help="Input files")
parser.add_argument('-d', "--delete", help="Delete csv files", action="store_true")

args = parser.parse_args()

out=args.output.replace(".xlsx","")


writer = pd.ExcelWriter(out+'.xlsx', engine='xlsxwriter', engine_kwargs={"options": {'strings_to_numbers': True}})
for file in args.inputs:
	try:
		df = pd.read_csv(file)
		f=os.path.basename(file).replace(".csv","")
		with open(file, 'r') as q:
			reader = csv.reader(q)
			for row in reader:
				header = row
				break

		df.to_excel(writer, sheet_name=f, index=False, header=header, float_format = "%0.2f")
		if args.delete:
			os.remove(file)
	except Exception as e:
		print(e)
		sys.exit(1)

writer.close()
