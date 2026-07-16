#! /usr/bin/env python
from openpyxl import load_workbook
import re
import math
from decimal import Decimal
from typing import Optional, Dict
import argparse

def tex_escape(s: str) -> str:
    s = str(s)
    s = s.replace('\\', '\\textbackslash{}')
    s = re.sub(r'([_%$#&{}])', r'\\\1', s)
    return s

def format_numeric(val, decimals: Optional[int]):
    if val is None:
        return ""
    try:
        if isinstance(val, float) and math.isnan(val):
            return ""
    except Exception:
        pass
    if decimals is None:
        return str(val)
    try:
        decimals = int(decimals)
        return f"{float(val):.{decimals}f}"
    except (ValueError, TypeError):
        return str(val)

def cell_to_latex(cell, col_decimals_map: Optional[Dict[int,int]] = None, default_decimals: Optional[int] = 2):
    raw_value = cell.value
    col_idx = cell.column if hasattr(cell, 'column') else cell.col_idx
    # Use column-specific decimals if defined, else default
    decimals = col_decimals_map[col_idx] if col_decimals_map and col_idx in col_decimals_map else default_decimals
    if isinstance(raw_value, (int, float, Decimal)):
        s = format_numeric(raw_value, decimals)
    else:
        s = tex_escape(raw_value if raw_value is not None else '')
    font = getattr(cell, 'font', None)
    if font is not None:
        if getattr(font, 'italic', False):
            s = f'\\textit{{{s}}}'
        if getattr(font, 'bold', False):
            s = f'\\textbf{{{s}}}'
    return s

def workbook_to_latex_matrix(path, sheet_name=None, sheet_number=None, data_only=True,
                             default_decimals: Optional[int] = 2,
                             col_decimals_map: Optional[Dict[int,int]] = None):
    wb = load_workbook(path, data_only=data_only)
    ws = wb[sheet_name] if sheet_name else wb.worksheets[sheet_number]

    max_row, max_col = ws.max_row, ws.max_column
    merged_map = {}
    multirow_track = {}

    for mr in ws.merged_cells.ranges:
        minr, minc, maxr, maxc = mr.min_row, mr.min_col, mr.max_row, mr.max_col
        for r in range(minr, maxr+1):
            for c in range(minc, maxc+1):
                if (r,c) == (minr,minc):
                    merged_map[(r,c)] = ('top', (maxr-minr+1, maxc-minc+1))
                else:
                    merged_map[(r,c)] = ('skip', (minr,minc))

    rows = []
    for r in range(1, max_row+1):
        row_cells = []
        c = 1
        while c <= max_col:
            while multirow_track.get(c, 0) > 0:
                row_cells.append('')
                multirow_track[c] -= 1
                c += 1

            if c > max_col:
                break

            key = (r,c)
            if merged_map.get(key, ('',))[0] == 'skip':
                c += 1
                continue

            cell = ws.cell(row=r, column=c)
            s = cell_to_latex(cell, col_decimals_map, default_decimals)

            if merged_map.get(key, ('',))[0] == 'top':
                nrows, ncols = merged_map[key][1]
                if ncols > 1:
                    s = f'\\multicolumn{{{ncols}}}{{c}}{{{s}}}'
                if nrows > 1:
                    s = f'\\multirow{{{nrows}}}{{*}}{{{s}}}'
                    for cc in range(c, c+ncols):
                        multirow_track[cc] = nrows - 1
                c += ncols
            else:
                c += 1
            row_cells.append(s)

        rows.append(' & '.join(row_cells) + r' \\')

    col_format = 'r' * max_col
    latex_str = '\\begin{tabular}{' + col_format + '}' + '\n'.join(rows) + '\\end{tabular}'
    return latex_str

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Excel sheet to LaTeX table")
    parser.add_argument('file')
    parser.add_argument('--decimals', type=int, default=2)
    parser.add_argument('--sheet_name', type=str, default=None)
    parser.add_argument('--sheet_number', type=int, default=None)
    parser.add_argument('--col_decimal', action='append')
    args = parser.parse_args()

    if not args.sheet_name and args.sheet_number is None:
        parser.error('Provide either --sheet_name or --sheet_number')

    col_dec_map = {}
    if args.col_decimal:
        for item in args.col_decimal:
            col, dec = item.split(':')
            try:
                col_dec_map[int(col)] = int(dec)
            except ValueError:
                col_dec_map[int(col)] = args.decimals

    latex_str = workbook_to_latex_matrix(args.file, args.sheet_name, args.sheet_number,
                                        default_decimals=args.decimals, col_decimals_map=col_dec_map)
    print(latex_str)