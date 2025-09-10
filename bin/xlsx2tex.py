#! /usr/bin/python3

import pandas as pd
import argparse
import re

def column_letter_to_index(letter):
    """Convert column letter (e.g., A, B, AA) to 0-based index."""
    letter = letter.upper()
    index = 0
    for char in letter:
        index = index * 26 + (ord(char) - ord('A') + 1)
    return index - 1

def parse_columns(columns):
    """Parse columns argument to handle ranges like A-D."""
    parsed_columns = []
    for col in columns:
        if '-' in col:
            start, end = col.split('-')
            start_idx = column_letter_to_index(start)
            end_idx = column_letter_to_index(end)
            parsed_columns.extend(range(start_idx, end_idx + 1))
        else:
            parsed_columns.append(column_letter_to_index(col))
    return parsed_columns

parser = argparse.ArgumentParser(description='xlsx2tex')
parser.add_argument("file", help="Input file")
parser.add_argument("-s", "--sheet", help="Sheet name or number (1-based index)", default=None)
parser.add_argument("--header", help="Number of header lines", default=2, type=int)
parser.add_argument("-f", "--float", help="Number of digits after the comma", default=2, type=int)
parser.add_argument("-c", "--columns", nargs='+', type=str, help="Columns to include (letters like A-D)")
parser.add_argument("-i", "--integer", nargs='+', type=str, help="Columns to treat as integers (letters like A-D)")

args = parser.parse_args()
header = [q for q in range(0, args.header)]

if args.sheet is None:
    sheet = 0
else:
    try:
        sheet = int(args.sheet) - 1  # Convert 1-based to 0-based index
    except ValueError:
        sheet = args.sheet

fo = open(args.file, "rb")
tab = pd.read_excel(fo, header=header, sheet_name=sheet, keep_default_na=True)

# Filter columns if --columns is provided
if args.columns:
    selected_columns = parse_columns(args.columns)
    tab = tab.iloc[:, selected_columns]

# Identify integer columns if --integer is provided
integer_columns = []
if args.integer:
    integer_columns = parse_columns(args.integer)
# Format columns based on their data type
for i, col in enumerate(tab.columns):
    if i in integer_columns:
        tab[col] = tab[col].apply(lambda x: "" if pd.isna(x) or str(x).strip() == "" else "{:.0f}".format(x))  # Format as integer
    elif pd.api.types.is_numeric_dtype(tab[col]):
        tab[col] = tab[col].apply(lambda x: "" if pd.isna(x) or str(x).strip() == "" else f"{{:.{args.float}f}}".format(x))  # Format as float
    else:
        tab[col] = tab[col].apply(lambda x: "" if pd.isna(x) or str(x).strip() == "" else x)  # Keep non-numeric columns as is

# Replace any remaining NaN or "nan" strings with empty strings
tab = tab.replace([pd.NA, "nan", "NaN"], "")


# Convert to LaTeX
out = tab.to_latex(index=False, multicolumn=True, multirow=True, na_rep='', float_format=None, column_format='r' * len(tab.columns), escape=False)
out = re.sub("Unnamed: \\S+", "", out)
out = re.sub("multicolumn{(\\d+)}{l}", r"multicolumn{\1}{c}", out)
print(out)