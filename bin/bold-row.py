import re
import sys
import argparse

parser = argparse.ArgumentParser(description='bold-row')
parser.add_argument("--minmax", help="Minimum or maximum", default="min")
parser.add_argument("--quali", help="all/even/odd", default="all")

args = parser.parse_args()


for line in sys.stdin:
	numbers = [float(s) for s in re.findall(r'-?\s*\b\d+(?:\.\d+)?\b', line)]
	if args.quali == "even":
		numbers = numbers[0::2]
	elif args.quali == "odd":
		numbers = numbers[1::2]

	line = line.rstrip()

	if len(numbers) > 0:
		if args.minmax == "min":
			m = min(numbers)
		else:
			m = max(numbers)

		line = re.sub(str(m), "\\\\bfseries "+str(m), line)

	print(line)