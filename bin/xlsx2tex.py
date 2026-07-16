#!/usr/bin/env python3
r"""
xlsx2tex.py - Convert an Excel sheet to a LaTeX table with robust formatting.

Features:
- Preserves MultiIndex headers so to_latex(..., multirow=True) can generate \multirow correctly.
- Cell-by-cell formatting for floats (controlled by -f / --float) to handle mixed dtypes.
- Option to specify integer columns (--integer) by name or 0-based index (comma-separated).
- Outputs to stdout by default or to a file with --out.
- Keeps control over column_format; auto-guesses right-alignment by default.
- Replaces only pandas' 'Unnamed' placeholders in header levels (safe).
"""

from __future__ import annotations
import argparse
import sys
import re
import pandas as pd
from typing import List, Set, Tuple

def parse_integer_columns(arg: str, df: pd.DataFrame) -> Set[int]:
    """
    Accepts a comma-separated string where each token is either:
      - an integer index (0-based)
      - an exact column name (for single-level columns)
      - a dotted name for MultiIndex levels (e.g., "Level1.Level2")
    Returns a set of integer column positions (0-based) to treat as integers.
    """
    if not arg:
        return set()
    s = set()
    tokens = [t.strip() for t in arg.split(",") if t.strip() != ""]
    cols = list(df.columns)
    for tok in tokens:
        # try integer index
        try:
            idx = int(tok)
            if 0 <= idx < len(cols):
                s.add(idx)
                continue
        except Exception:
            pass

        # try to match by string representation of the column object
        # for MultiIndex columns, join with '.' for matching convenience
        matched = False
        for i, c in enumerate(cols):
            key = c if not (isinstance(c, tuple)) else ".".join(str(x) for x in c)
            if key == tok:
                s.add(i)
                matched = True
                break
        if not matched:
            # last resort: try substring match (dangerous but sometimes useful)
            for i, c in enumerate(cols):
                key = c if not (isinstance(c, tuple)) else ".".join(str(x) for x in c)
                if tok in key:
                    s.add(i)
                    matched = True
                    break
        if not matched:
            # ignore unknown token but warn
            print(f"Warning: integer column token '{tok}' not recognized; ignored.", file=sys.stderr)
    return s

UNNAMED_HEADER_RE = re.compile(r"Unnamed: \d+(_level_\d+)?")


def normalize_header_value(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value)
    if UNNAMED_HEADER_RE.fullmatch(text):
        return ""
    return text


def detect_header_groups(columns: pd.Index, start_col: int) -> List[Tuple[int, int]]:
    if not isinstance(columns, pd.MultiIndex) or columns.nlevels < 2:
        return []

    if start_col < 0 or start_col >= len(columns):
        return []

    top_level = [normalize_header_value(col[0]) for col in columns]
    groups: List[Tuple[int, int]] = []
    i = start_col

    while i < len(columns):
        label = top_level[i]
        if label == "":
            i += 1
            continue

        j = i + 1
        while j < len(columns) and top_level[j] == label:
            j += 1
        groups.append((i, j - 1))
        i = j

    return groups


def insert_group_separators(
    df: pd.DataFrame, start_col: int
) -> Tuple[pd.DataFrame, List[int], List[Tuple[int, int]]]:
    groups = detect_header_groups(df.columns, start_col)
    if len(groups) < 2:
        return df, [], []

    separator_after = {end for _, end in groups[:-1]}
    last_group_end = {end: idx for idx, (_, end) in enumerate(groups)}
    separator_label = tuple("" for _ in range(df.columns.nlevels))

    pieces = []
    new_columns = []
    separator_positions: List[int] = []
    orig_to_latex_col = {}
    latex_col = 0

    for pos in range(len(df.columns)):
        col = df.columns[pos]
        pieces.append(df.iloc[:, pos].rename(col))
        new_columns.append(col)
        latex_col += 1
        orig_to_latex_col[pos] = latex_col

        if pos in separator_after:
            pieces.append(pd.Series([""] * len(df), index=df.index, name=separator_label))
            new_columns.append(separator_label)
            latex_col += 1
            separator_positions.append(latex_col)

    out = pd.concat(pieces, axis=1)
    out.columns = pd.MultiIndex.from_tuples(new_columns)

    cmidrules = []
    for start, end in groups:
        cmidrules.append((orig_to_latex_col[start], orig_to_latex_col[end]))

    return out, separator_positions, cmidrules


def expand_column_format(column_format: str, separator_positions: List[int], expected_columns: int) -> str:
    if not separator_positions:
        return column_format

    if len(column_format) != expected_columns or any(ch not in "lcr" for ch in column_format):
        print(
            "Warning: custom --column-format left unchanged; separator columns may need manual alignment.",
            file=sys.stderr,
        )
        return column_format

    chars = list(column_format)
    for offset, pos in enumerate(separator_positions):
        chars.insert(pos - 1, "c")
    return "".join(chars)


def inject_cmidrules(latex: str, cmidrule_ranges: List[Tuple[int, int]]) -> str:
    if not cmidrule_ranges:
        return latex

    lines = latex.splitlines()
    try:
        top_idx = next(i for i, line in enumerate(lines) if line.strip() == r"\toprule")
    except StopIteration:
        return latex

    if top_idx + 2 >= len(lines):
        return latex

    cmidrule_line = " ".join(
        rf"\cmidrule(lr){{{start}-{end}}}" for start, end in cmidrule_ranges
    )
    lines.insert(top_idx + 2, cmidrule_line)
    return "\n".join(lines)

def main():
    p = argparse.ArgumentParser(description="Convert an Excel sheet to LaTeX (robust float & multirow support).")
    p.add_argument("xlsx", help="Excel file path")
    p.add_argument("--sheet", "-s", default=0, help="Sheet name or index (default: 0)")
    p.add_argument("--header", "-H", type=int, default=0, help="Number of header rows (0 = no header, 1 = single header). If >1, will use that many rows as header. Default: 0")
    p.add_argument("-f", "--float", type=int, default=2, help="Number of decimal digits for floats (default: 2)")
    p.add_argument("--integer", "-i", default="", help="Comma-separated list of integer columns (names or 0-based indices).")
    p.add_argument("--out", "-o", default=None, help="Output file (default stdout)")
    p.add_argument("--escape", action="store_true", help="Escape LaTeX special characters in cell text (default: False - keep raw)")
    p.add_argument("--column-format", default=None, help="LaTeX column format string (e.g. 'lcr'). If omitted auto-creates 'r' repeated.")
    p.add_argument("--na-rep", default="", help="Representation for NA values (default empty)")
    p.add_argument(
        "--algorithm-groups-start",
        type=int,
        default=None,
        help=(
            "0-based index of the first column belonging to grouped top headers. "
            "When set, inserts an empty separator column between contiguous groups "
            "in the first header row and adds matching \\cmidrule entries. "
            "Requires at least 2 header rows."
        ),
    )
    args = p.parse_args()

    # Read sheet. If header==0, pandas still needs header=0 or None
    header_arg = 0 if args.header >= 1 else None
    try:
        df = pd.read_excel(args.xlsx, sheet_name=args.sheet, header=header_arg)
    except Exception as e:
        print(f"Error reading Excel file: {e}", file=sys.stderr)
        sys.exit(2)

    # If header rows >1 we need to construct a MultiIndex from the top `header` rows manually
    if args.header > 1:
        # Re-read to get top header rows + data
        # pandas.read_excel with header=list(range(n)) works, but some excel quirks exist; try it:
        try:
            df = pd.read_excel(args.xlsx, sheet_name=args.sheet, header=list(range(args.header)))
        except Exception:
            # fallback: read everything then build MultiIndex from the first header rows
            tmp = pd.read_excel(args.xlsx, sheet_name=args.sheet, header=None)
            header_tuples = []
            for col in tmp.columns:
                levels = []
                for r in range(args.header):
                    val = tmp.iat[r, col]
                    # convert nan to empty string for header level
                    if pd.isna(val):
                        val = ""
                    levels.append(str(val))
                header_tuples.append(tuple(levels))
            data = tmp.iloc[args.header:].reset_index(drop=True)
            df = pd.DataFrame(data.values, columns=pd.MultiIndex.from_tuples(header_tuples))

    # If header==0, ensure columns are simple strings (0..n-1) so downstream matching works
    if args.header == 0:
        df.columns = [str(c) for c in df.columns]

    # Determine integer columns by positions
    integer_positions = parse_integer_columns(args.integer, df)

    # Define formatters (cell-by-cell)
    float_digits = max(0, args.float)

    def fmt_int(x):
        try:
            if pd.isna(x) or str(x).strip() == "":
                return args.na_rep
            return f"{int(round(float(x))):d}"
        except Exception:
            # fallback keep original string
            return str(x)

    def fmt_float_val(x):
        try:
            if pd.isna(x) or str(x).strip() == "":
                return args.na_rep
            return f"{float(x):.{float_digits}f}"
        except Exception:
            return str(x)

    def escape_latex(s: str) -> str:
        # only escape when requested
        if not args.escape:
            return s
        # minimal escaping for LaTeX special chars
        esc_map = {
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\^{}",
            "\\": r"\textbackslash{}",
        }
        out = str(s)
        for k, v in esc_map.items():
            out = out.replace(k, v)
        return out

    # Apply formatting cell-by-cell into a new DataFrame of strings
    out_df = pd.DataFrame(columns=df.columns)

    for i, col in enumerate(df.columns):
        series = df[col]
        # build the formatted column as strings
        formatted = []
        for v in series:
            # NA handling
            if pd.isna(v) or (isinstance(v, str) and v.strip() == ""):
                out_val = args.na_rep
            else:
                if i in integer_positions:
                    out_val = fmt_int(v)
                else:
                    # try numeric detection: if value is numeric or looks numeric, format as float
                    formatted_as_float = False
                    try:
                        # handle pandas types and strings representing numbers
                        _ = float(v)
                        formatted_as_float = True
                    except Exception:
                        formatted_as_float = False

                    if formatted_as_float:
                        out_val = fmt_float_val(v)
                    else:
                        out_val = str(v)
            out_val = escape_latex(out_val)
            formatted.append(out_val)
        out_df[col] = formatted

    # Make sure columns keep the same type (Index or MultiIndex)
    out_df.columns = df.columns

    separator_positions: List[int] = []
    cmidrule_ranges: List[Tuple[int, int]] = []
    original_column_count = len(out_df.columns)
    if args.algorithm_groups_start is not None:
        if not isinstance(out_df.columns, pd.MultiIndex) or out_df.columns.nlevels < 2:
            print(
                "Warning: --algorithm-groups-start ignored because the table does not have at least 2 header rows.",
                file=sys.stderr,
            )
        else:
            out_df, separator_positions, cmidrule_ranges = insert_group_separators(
                out_df, args.algorithm_groups_start
            )
            if not cmidrule_ranges:
                print(
                    "Warning: no grouped headers detected from --algorithm-groups-start; table left unchanged.",
                    file=sys.stderr,
                )

    # Column format
    if args.column_format:
        column_format = expand_column_format(args.column_format, separator_positions, original_column_count)
    else:
        # default: right align all columns (common for numeric tables)
        column_format = " ".join(["r"] * len(out_df.columns))
        # remove spaces for pandas compatibility
        column_format = column_format.replace(" ", "")

    # Convert DataFrame to LaTeX. We pass multirow=True so pandas will use \multirow where appropriate.
    # We set escape=False because we applied escaping already (or not) in escape_latex.
    try:
        latex = out_df.to_latex(index=False, multicolumn=True, multirow=True, na_rep=args.na_rep,
                                float_format=None, column_format=column_format, escape=False)
    except Exception as e:
        print(f"Error converting to LaTeX via pandas.to_latex: {e}", file=sys.stderr)
        sys.exit(3)

    # Post-processing: remove only pandas' Unnamed placeholders in header levels (safer)
    # Examples:
    #   Unnamed: 0_level_0
    #   Unnamed: 1
    latex = UNNAMED_HEADER_RE.sub("", latex)

    # Common tweak: center grouped headers regardless of the original column alignment.
    latex = re.sub(r"\\multicolumn{(\d+)}{[lrc]}", r"\\multicolumn{\1}{c}", latex)

    latex = inject_cmidrules(latex, cmidrule_ranges)

    # Tidy up repeated spaces introduced by empty header cells
    # (optional: compress multiple spaces in & separators)
    latex = re.sub(r"(\s*&\s*){2,}", lambda m: " & ".join([""] * (m.group(0).count("&") + 1)), latex)

    # Output
    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(latex)
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(4)
    else:
        # stdout
        sys.stdout.write(latex)

if __name__ == "__main__":
    main()
