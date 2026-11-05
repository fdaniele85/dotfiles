#! /home/daniele/.venvs/scripts_1553aca88f67/bin/python3
# encoding: utf-8

import os
import sys
import re
import json
import argparse
import csv
import importlib
import math
import posixpath
import tempfile
import zipfile
import xml.etree.ElementTree as ET
import objectpath
import numpy as np
import random
import pandas as pd
from natsort import natsorted, ns
from tqdm import tqdm

"""
Script che estrae valori da JSON (objectpath), aggrega con pandas e scrive una tabella CSV.
- Rimosso il supporto a bigTypes.
- Usa DataFrame + groupby/agg + unstack (pivot) per calcoli più semplici.
- Flag --to-parquet per salvare il dataframe raw (records) su disco.

Uso essenziale:
  script.py --arguments 'field' --mean --median --std <dirs...>
  script.py --arguments 'field' --mean --time-limit 60 --incumbent-time time <dirs...>
  script.py --onlyOne <dirs...>

Nota: lo script richiede pandas.
"""


def round_floats(row, digits):
    rounded_row = []
    for x in row:
        if isinstance(x, float) or isinstance(x, np.floating):
            rounded_row.append(f"{x:.{digits}f}")
        else:
            rounded_row.append(x)
    return rounded_row


def safe_execute(tree, expr):
    try:
        res = tree.execute(expr)
    except Exception:
        raise

    if res is None:
        raise ValueError("None result")

    try:
        if hasattr(res, "__iter__") and not isinstance(res, (str, bytes, dict)):
            lst = list(res)
            if len(lst) == 0:
                raise ValueError("empty")
            if len(lst) == 1:
                return lst[0]
            return lst
    except TypeError:
        pass

    return res


def execute_preserve_shape(tree, expr):
    res = tree.execute(expr)
    if res is None:
        raise ValueError("None result")

    try:
        if hasattr(res, "__iter__") and not isinstance(res, (str, bytes, dict, list, tuple)):
            return list(res)
    except TypeError:
        pass

    return res


def parse_args():
    p = argparse.ArgumentParser(description='test')
    group = p.add_mutually_exclusive_group()
    group.add_argument("--empty", help="Print rows with empty values", action="store_true")
    group.add_argument("--complete", help="Print only rows with values for all algorithms", action="store_true")
    p.add_argument("--arguments", nargs='+', help="Arguments")
    p.add_argument(
        "--time-limit",
        type=float,
        help="Extract --arguments from the last incumbent whose time is not greater than this value.",
    )
    p.add_argument(
        "--incumbent-time",
        help="Objectpath expression, relative to an incumbent, containing its time.",
    )
    p.add_argument(
        "--incumbents-path",
        default="incumbents",
        help="Objectpath expression containing the incumbent array (default: incumbents).",
    )
    p.add_argument(
        "--best-by",
        help="Select the best run for each instance using this objectpath expression. "
             "Mutually exclusive with aggregation/print flags; with --best-by, --max means select the largest value instead of the smallest.",
    )
    p.add_argument(
        "--solution",
        help="Objectpath expression to print alongside --best-by. Required with --best-by and accepted only with --best-by.",
    )
    p.add_argument("inputs", nargs='+', help="Input directories (will keep only existing dirs)")
    p.add_argument("-o", "--out", nargs='+', help="Output Excel file and optional sheet name")
    p.add_argument("--type", help="Type regex", default=r"_\d+\.ris$")
    p.add_argument("--replace", help="Replace", default="")
    p.add_argument("-g", "--grep", help="Grep")
    p.add_argument("-v", help="Grep reverse", action="store_true")
    p.add_argument("--onlyOne", help="Print only one", action="store_true")
    p.add_argument("--stddev", help="Print std dev", action="store_true")
    p.add_argument("--median", help="Print median", action="store_true")
    p.add_argument("--mean", help="Print average", action="store_true")
    p.add_argument("--min", help="Print min", action="store_true")
    p.add_argument(
        "--max",
        help="In aggregation mode, print max. With --best-by, select the largest value instead of the smallest.",
        action="store_true",
    )
    p.add_argument("--count", help="Print the count", action="store_true")
    p.add_argument("-n", "--names", nargs='+', help="Algorithms' names")
    p.add_argument("--column-names", nargs='+', help="Custom column names for --arguments")
    p.add_argument("--check", help="Feasibility check (objectpath expr)")
    p.add_argument("--full", help="Full names", action="store_true")
    p.add_argument("--size", help="Check if an array has size greater than zero (objectpath expr)")
    p.add_argument("--to-parquet", help="Save raw extracted records as parquet (path)")
    p.add_argument("--columnMean", help="Print column means at end of CSV", action="store_true")
    p.add_argument("--gap", help="Print gap row after mean (implies --columnMean)", action="store_true")
    p.add_argument("--digits", help="Number of digits for rounding floats in output", type=int, default=2)
    p.add_argument(
        "--first",
        nargs='+',
        help="Keep first N runs ordered by an objectpath metric: ARG N [min|max]",
    )
    p.add_argument("--silent", help="Disable per-file path logging", action="store_true")
    return p.parse_args()


def format_json_compact_lists(obj, indent=2, level=0):
    sp = " " * (indent * level)
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        lines = ["{"]
        last_idx = len(obj) - 1
        for idx, (k, v) in enumerate(obj.items()):
            key_txt = json.dumps(k, ensure_ascii=False)
            val_txt = format_json_compact_lists(v, indent=indent, level=level + 1)
            comma = "," if idx < last_idx else ""
            lines.append(" " * (indent * (level + 1)) + f"{key_txt}: {val_txt}{comma}")
        lines.append(sp + "}")
        return "\n".join(lines)
    if isinstance(obj, (list, tuple)):
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(obj, ensure_ascii=False)


def get_input_display_name(path):
    return os.path.basename(os.path.normpath(path))


def matches_grep(typ, grep, grep_invert):
    if not grep:
        return True
    matched = re.search(grep, typ) is not None
    return not matched if grep_invert else matched


def collect_ris_entries(input_path, type_regex, replace, grep, grep_invert):
    entries = []
    try:
        files = os.listdir(input_path)
    except OSError as exc:
        sys.stderr.write(f"Cannot list {input_path}: {exc}\n")
        return entries

    for file_name in files:
        if not file_name.endswith("ris"):
            continue
        typ = re.sub(type_regex, replace, file_name)
        if not matches_grep(typ, grep, grep_invert):
            continue
        path = os.path.join(input_path, file_name)
        entries.append({
            "source": input_path,
            "file_name": file_name,
            "typ": typ,
            "path": path,
        })
    return entries


def select_incumbent_at_time(tree, incumbents_expr, time_expr, time_limit):
    incumbents = execute_preserve_shape(tree, '$.' + incumbents_expr)
    if not isinstance(incumbents, (list, tuple)):
        incumbents = list(incumbents)

    selected = None
    for incumbent in incumbents:
        if not isinstance(incumbent, dict):
            continue
        try:
            incumbent_tree = objectpath.Tree(incumbent)
            incumbent_time = safe_execute(incumbent_tree, '$.' + time_expr)
            if not isinstance(incumbent_time, (int, float, np.number)):
                continue
            if float(incumbent_time) <= time_limit:
                selected = incumbent
        except Exception:
            continue

    return selected


def open_ris_entry(entry):
    return open(entry["path"], "r", encoding="utf-8")


def read_excel_formula_results(path):
    """Keep existing formula caches when openpyxl rewrites a workbook."""
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    rel_ns = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    results = {}
    with zipfile.ZipFile(path) as source:
        workbook = ET.fromstring(source.read('xl/workbook.xml'))
        relationships = ET.fromstring(source.read('xl/_rels/workbook.xml.rels'))
        targets = {item.get('Id'): item.get('Target') for item in relationships}
        for sheet in workbook.findall('s:sheets/s:sheet', ns):
            target = targets[sheet.get('{' + rel_ns + '}id')]
            worksheet_path = (target.lstrip('/') if target.startswith('/')
                              else posixpath.normpath(posixpath.join('xl', target)))
            # Chartsheets do not contain worksheet cells.
            worksheet = ET.fromstring(source.read(worksheet_path))
            cached = {}
            for cell in worksheet.findall('.//s:c', ns):
                value = cell.find('s:v', ns)
                if cell.find('s:f', ns) is None or value is None:
                    continue
                cached[cell.get('r')] = (cell.get('t'), value.text)
            results[sheet.get('name')] = cached
    return results


def cache_excel_formula_results(path, sheet_name, results):
    """Add formula caches to an XLSX written by openpyxl (which cannot set them)."""
    if not results:
        return
    spreadsheet_ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    document_rel_ns = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    package_rel_ns = 'http://schemas.openxmlformats.org/package/2006/relationships'
    tag = lambda name: '{' + spreadsheet_ns + '}' + name
    temporary_path = None
    try:
        with zipfile.ZipFile(path) as source:
            workbook = ET.fromstring(source.read('xl/workbook.xml'))
            sheet = next(item for item in workbook.find(tag('sheets'))
                         if item.get('name') == sheet_name)
            relationship_id = sheet.get('{' + document_rel_ns + '}id')
            relationships = ET.fromstring(source.read('xl/_rels/workbook.xml.rels'))
            relationship = next(item for item in relationships.findall('{' + package_rel_ns + '}Relationship')
                                if item.get('Id') == relationship_id)
            target = relationship.get('Target')
            worksheet_path = (target.lstrip('/') if target.startswith('/')
                              else posixpath.normpath(posixpath.join('xl', target)))
            worksheet = ET.fromstring(source.read(worksheet_path))
            pending = dict(results)
            for cell in worksheet.iter(tag('c')):
                reference = cell.get('r')
                if reference not in pending:
                    continue
                if cell.find(tag('f')) is None:
                    raise ValueError(f"Expected a formula in {sheet_name}!{reference}")
                result = pending.pop(reference)
                value = cell.find(tag('v'))
                if value is None:
                    value = ET.SubElement(cell, tag('v'))
                if isinstance(result, tuple):
                    # Preserve the original cached type (including errors/bools).
                    value_type, value.text = result
                    if value_type is None:
                        cell.attrib.pop('t', None)
                    else:
                        cell.set('t', value_type)
                elif result == '':
                    cell.set('t', 'str')
                    value.text = None
                else:
                    cell.attrib.pop('t', None)
                    value.text = repr(float(result))
            if pending:
                raise ValueError(f"Missing formula cells: {', '.join(pending)}")
            worksheet_xml = ET.tostring(worksheet, encoding='utf-8', xml_declaration=True)
            with tempfile.NamedTemporaryFile(
                    dir=os.path.dirname(os.path.abspath(path)), suffix='.xlsx', delete=False) as temporary:
                temporary_path = temporary.name
            with zipfile.ZipFile(temporary_path, 'w') as destination:
                destination.comment = source.comment
                for item in source.infolist():
                    destination.writestr(item, worksheet_xml if item.filename == worksheet_path
                                         else source.read(item.filename))
        os.chmod(temporary_path, os.stat(path).st_mode & 0o777)
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            os.unlink(temporary_path)


def main():
    args = parse_args()

    if not args.onlyOne and not args.arguments and not args.best_by:
        sys.exit("--arguments is required unless --onlyOne is set.")

    if args.gap:
        args.columnMean = True

    inputs = [dr for dr in args.inputs if os.path.isdir(dr)]
    if not inputs:
        sys.exit("No valid input directories provided.")

    richiesti = args.arguments or []
    typeRegex = args.type
    replace = args.replace or ""
    empty = args.empty
    complete = args.complete
    onlyOne = args.onlyOne
    stddev = args.stddev
    names = args.names
    column_names = args.column_names
    check = args.check
    size_expr = args.size
    count_flag = args.count
    full = args.full
    grep = args.grep
    grep_invert = args.v
    silent = args.silent
    best_by = args.best_by
    solution_expr = args.solution
    time_limit = args.time_limit
    incumbent_time = args.incumbent_time
    incumbents_path = args.incumbents_path

    if (time_limit is None) != (incumbent_time is None):
        sys.exit("--time-limit and --incumbent-time must be used together.")
    if time_limit is not None and not richiesti:
        sys.exit("--time-limit requires --arguments.")
    if time_limit is not None and best_by:
        sys.exit("--time-limit cannot be used with --best-by.")

    if not onlyOne and best_by and not solution_expr:
        sys.exit("--solution is required with --best-by.")
    if not onlyOne and solution_expr and not best_by:
        sys.exit("--solution can be used only with --best-by.")
    if best_by and not onlyOne:
        incompatible_flags = []
        if args.arguments:
            incompatible_flags.append("--arguments")
        if args.empty:
            incompatible_flags.append("--empty")
        if complete:
            incompatible_flags.append("--complete")
        if args.mean:
            incompatible_flags.append("--mean")
        if args.median:
            incompatible_flags.append("--median")
        if stddev:
            incompatible_flags.append("--stddev")
        if count_flag:
            incompatible_flags.append("--count")
        if args.min:
            incompatible_flags.append("--min")
        if args.first:
            incompatible_flags.append("--first")
        if args.columnMean:
            incompatible_flags.append("--columnMean")
        if args.gap:
            incompatible_flags.append("--gap")
        if column_names:
            incompatible_flags.append("--column-names")
        if full:
            incompatible_flags.append("--full")
        if incompatible_flags:
            sys.exit("--best-by is mutually exclusive with: " + ", ".join(incompatible_flags))

    first_arg = None
    first_n = None
    first_dir = "min"
    if args.first:
        if len(args.first) < 2 or len(args.first) > 3:
            sys.exit("--first requires 2 or 3 arguments: ARG N [min|max]")
        first_arg = args.first[0]
        try:
            first_n = int(args.first[1])
            if first_n <= 0:
                raise ValueError("n must be > 0")
        except Exception:
            sys.exit("--first N must be a positive integer")
        if len(args.first) == 3:
            first_dir = args.first[2].lower()
        if first_dir not in ("min", "max"):
            sys.exit("--first third argument must be 'min' or 'max'")

    # writer
    out_path = args.out
    writer = None

    if args.digits < 0:
        sys.exit("--digits must be non-negative.")
    if time_limit is not None and (not math.isfinite(time_limit) or time_limit < 0):
        sys.exit("--time-limit must be finite and non-negative.")
    try:
        type_pattern = re.compile(typeRegex)
        # Validate replacement backreferences even when there are no files.
        type_pattern.sub(replace, '')
        if grep is not None:
            re.compile(grep)
    except (re.error, IndexError) as exc:
        sys.exit(f"Invalid --type/--replace or --grep: {exc}")

    # Validate command options before listing or loading result files.
    metrics = []
    order_metrics = []
    for enabled, metric in (
        (args.mean, 'mean'),
        (args.median, 'median'),
        (stddev, 'std'),
        (count_flag, 'count'),
        (args.min, 'min'),
        (args.max, 'max'),
    ):
        if enabled:
            metrics.append((metric, metric))
            order_metrics.append(metric)

    if not onlyOne:
        if not best_by and not metrics:
            sys.exit("No aggregation flag requested (e.g. --mean, --median, ...).")
        if out_path is not None:
            if best_by:
                if len(out_path) != 1:
                    sys.exit("--out with --best-by requires exactly one CSV output path.")
                if not out_path[0].lower().endswith('.csv'):
                    sys.exit("--out with --best-by supports only .csv output.")
            else:
                if len(out_path) not in (1, 2):
                    sys.exit("--out requires 1 or 2 arguments: FILE [SHEET]")
                if not out_path[0].lower().endswith(('.xlsx', '.xls')):
                    sys.exit("--out supports only .xlsx or .xls output")
                if (len(out_path) == 2 and os.path.exists(out_path[0])
                        and out_path[0].lower().endswith('.xls')):
                    sys.exit("Appending/replacing sheets is not supported for .xls. Use .xlsx instead.")

                sheet_name = out_path[1] if len(out_path) == 2 else None
                sheet_to_use = sheet_name or "Sheet1"
                if (len(sheet_to_use) > 31 or re.search(r'[\[\]:*?/\\]', sheet_to_use)
                        or sheet_to_use.startswith("'") or sheet_to_use.endswith("'")):
                    sys.exit("Invalid Excel sheet name (maximum 31 characters; no []:*?/\\ or leading/trailing apostrophe).")
                mode = 'a' if sheet_name and os.path.exists(out_path[0]) else 'w'
                if_sheet_exists = 'replace' if mode == 'a' else None
                if mode == 'a':
                    engine = 'openpyxl'
                elif out_path[0].lower().endswith('.xls'):
                    engine = 'xlwt'
                else:
                    try:
                        importlib.import_module('xlsxwriter')
                        engine = 'xlsxwriter'
                    except ImportError:
                        engine = 'openpyxl'
                try:
                    importlib.import_module(engine)
                    pd.io.excel._util.get_writer(engine)
                except (ImportError, ValueError) as exc:
                    sys.exit(f"Excel engine {engine} is unavailable: {exc}")
                if mode == 'a':
                    try:
                        workbook = importlib.import_module('openpyxl').load_workbook(
                            out_path[0], read_only=True,
                        )
                        workbook.close()
                    except Exception as exc:
                        sys.exit(f"Cannot read existing Excel file {out_path[0]}: {exc}")

        output_targets = ([out_path[0]] if out_path else [])
        if args.to_parquet and not best_by:
            output_targets.append(args.to_parquet)
            try:
                from pandas.io.parquet import get_engine
                get_engine('auto')
            except ImportError as exc:
                sys.exit(f"Parquet engine is unavailable: {exc}")
        for target in output_targets:
            parent = os.path.dirname(os.path.abspath(target))
            if not os.path.isdir(parent) or not os.access(parent, os.W_OK):
                sys.exit(f"Output directory does not exist or is not writable: {parent}")
            if os.path.exists(target) and (not os.path.isfile(target) or not os.access(target, os.W_OK)):
                sys.exit(f"Output path is not a writable file: {target}")

    # prepare display names
    nomi = {}
    if names:
        for i, dr in enumerate(inputs):
            if i < len(names):
                nomi[dr] = names[i]
            else:
                nomi[dr] = get_input_display_name(dr)
    else:
        for dr in inputs:
            nomi[dr] = get_input_display_name(dr)

    # prepare display names for arguments (columns)
    arg_display = {}
    for i, arg in enumerate(richiesti):
        if column_names and i < len(column_names):
            arg_display[arg] = column_names[i]
        else:
            arg_display[arg] = arg

    # collect raw records
    records = []
    run_scores = []
    types_set = set()
    all_entries = []

    for dr in inputs:
        all_entries.extend(collect_ris_entries(dr, typeRegex, replace, grep, grep_invert))

    if onlyOne:
        if not all_entries:
            sys.exit("No records extracted.")
        entry = random.choice(all_entries)
        try:
            with open_ris_entry(entry) as fh:
                try:
                    a = json.load(fh)
                except json.JSONDecodeError:
                    sys.exit("Selected file is not valid JSON.")
                if not silent:
                    sys.stderr.write(entry["path"] + "\n")
                print(format_json_compact_lists(a, indent=2))
                sys.exit(0)
        except (IOError, OSError) as e:
            sys.exit(f"Cannot open {entry['path']}: {e}")

    entries_iter = all_entries
    if not silent:
        entries_iter = tqdm(all_entries, file=sys.stderr, unit="file")

    for entry in entries_iter:
        dr = entry["source"]
        fil = entry["file_name"]
        typ = entry["typ"]
        path = entry["path"]
        types_set.add(typ)

        try:
            with open_ris_entry(entry) as fh:
                try:
                    a = json.load(fh)
                except json.JSONDecodeError:
                    continue

                tree = objectpath.Tree(a)

                if check is not None:
                    try:
                        if not bool(tree.execute('$.' + check)):
                            continue
                    except Exception:
                        continue

                if size_expr is not None:
                    try:
                        seq = tree.execute('$.' + size_expr)
                        if hasattr(seq, "__len__"):
                            l = len(seq)
                        else:
                            l = len(list(seq))
                        if l <= 0:
                            continue
                    except Exception:
                        continue

                run_id = path
                if best_by is not None:
                    try:
                        best_val = safe_execute(tree, '$.' + best_by)
                    except Exception:
                        continue

                    if isinstance(best_val, (int, float, np.number)):
                        best_num = float(best_val)
                    elif isinstance(best_val, list) and len(best_val) == 1 and isinstance(best_val[0], (int, float, np.number)):
                        best_num = float(best_val[0])
                    else:
                        continue

                    try:
                        solution_val = execute_preserve_shape(tree, '$.' + solution_expr)
                    except Exception:
                        continue

                    records.append({
                        'dir': nomi[dr],
                        'typ': typ,
                        'value': best_num,
                        'solution': solution_val,
                        'run_id': run_id,
                    })
                    continue

                if first_arg is not None:
                    score_val = None
                    try:
                        score_val = safe_execute(tree, '$.' + first_arg)
                    except Exception:
                        score_val = None
                    score_num = None
                    if isinstance(score_val, (int, float, np.number)):
                        score_num = float(score_val)
                    elif isinstance(score_val, list) and len(score_val) == 1 and isinstance(score_val[0], (int, float, np.number)):
                        score_num = float(score_val[0])
                    if score_num is None:
                        continue
                    run_scores.append({'dir': nomi[dr], 'typ': typ, 'run_id': run_id, 'score': score_num})

                argument_tree = tree
                if time_limit is not None:
                    try:
                        selected_incumbent = select_incumbent_at_time(
                            tree,
                            incumbents_path,
                            incumbent_time,
                            time_limit,
                        )
                    except Exception:
                        continue
                    if selected_incumbent is None:
                        continue
                    argument_tree = objectpath.Tree(selected_incumbent)

                for arg in richiesti:
                    m = re.search(r'^(.*)\s*\|\s*length$', arg)
                    want_length = False
                    expr = arg
                    if m:
                        expr = m.group(1)
                        want_length = True

                    try:
                        val = safe_execute(argument_tree, '$.' + expr)
                    except Exception:
                        continue

                    if want_length:
                        try:
                            if hasattr(val, "__len__"):
                                x = len(val)
                            else:
                                x = 1
                        except Exception:
                            x = 0
                        records.append({'dir': nomi[dr], 'typ': typ, 'arg': arg, 'value': float(x), 'run_id': run_id})
                    else:
                        if isinstance(val, list) and val and all(isinstance(i, (int, float, np.number)) for i in val):
                            for i in val:
                                records.append({'dir': nomi[dr], 'typ': typ, 'arg': arg, 'value': float(i), 'run_id': run_id})
                        elif isinstance(val, (int, float, np.number)):
                            records.append({'dir': nomi[dr], 'typ': typ, 'arg': arg, 'value': float(val), 'run_id': run_id})

        except (IOError, OSError) as e:
            sys.stderr.write(f"Cannot open {path}: {e}\n")
            continue

    if not records:
        sys.exit("No records extracted.")

    if best_by is not None:
        best_rows = {}
        choose_max = args.max
        for record in records:
            typ = record['typ']
            current = best_rows.get(typ)
            if current is None:
                best_rows[typ] = record
                continue
            if choose_max:
                if record['value'] > current['value']:
                    best_rows[typ] = record
            else:
                if record['value'] < current['value']:
                    best_rows[typ] = record

        if not best_rows:
            sys.exit("No records extracted.")

        out_writer = None
        csvfile = None
        if out_path is None:
            out_writer = csv.writer(sys.stdout, delimiter=',')
        else:
            out_args = args.out
            out_path_single = out_args[0]
            csvfile = open(out_path_single, 'w', newline='', encoding='utf-8')
            out_writer = csv.writer(csvfile, delimiter=',')

        try:
            out_writer.writerow(['Instance', 'Value', 'Solution'])
            for typ in natsorted(best_rows.keys(), alg=ns.IGNORECASE):
                out_writer.writerow([
                    typ,
                    f"{best_rows[typ]['value']:.{args.digits}f}",
                    json.dumps(best_rows[typ]['solution'], ensure_ascii=False),
                ])
        finally:
            if csvfile is not None:
                csvfile.close()
        return

    df = pd.DataFrame.from_records(records)

    if first_arg is not None:
        df_scores = pd.DataFrame.from_records(run_scores)
        if df_scores.empty:
            sys.exit("No runs matched --first criteria.")
        ascending = True if first_dir == "min" else False
        df_scores = df_scores.sort_values(['dir', 'typ', 'score'], ascending=[True, True, ascending])
        selected = df_scores.groupby(['dir', 'typ'], sort=False).head(first_n)
        df = df.merge(selected[['dir', 'typ', 'run_id']], on=['dir', 'typ', 'run_id'], how='inner')
        if df.empty:
            sys.exit("No records after --first filtering.")

    # salvare raw dataframe in parquet se richiesto
    if args.to_parquet:
        try:
            df_parquet = df.rename(columns={"dir": "algorithm", "typ": "instance", "arg": "parameter", "value": "value", "run_id": "run_id"})
            df_parquet.to_parquet(args.to_parquet, index=False)
            sys.stderr.write(f"Saved parquet to {args.to_parquet}\n")
            # df.to_parquet(args.to_parquet, index=False)
            # sys.stderr.write(f"Saved parquet to {args.to_parquet}\n")
        except Exception as e:
            sys.stderr.write(f"Failed to save parquet: {e}\n")

    # groupby + agg -> DataFrame with MultiIndex (typ, dir, arg)
    agg_map = { 'value': [m[0] for m in metrics] }
    grouped = df.groupby(['typ', 'dir', 'arg'])['value'].agg([m[0] for m in metrics])

    # unstack dir and arg -> index=typ, columns MultiIndex (metric, dir, arg)
    pivoted = grouped.unstack(['dir', 'arg'])

    types_list = natsorted(list(types_set), alg=ns.IGNORECASE)
    trovati = [nomi[dr] for dr in inputs if dr in nomi]

    # costruzione header simile alla versione precedente
    quanti = len(order_metrics)
    righe = []
    field_top = ['']
    for alg in trovati:
        field_top.append(alg)
        for i in range(0, len(richiesti)):
            if i == 0:
                end = quanti - 1
            else:
                end = quanti
            for l in range(0, end):
                field_top.append("")
    if not full:
        righe.append(field_top)

    header2 = ['instance']
    for alg in trovati:
        for q in richiesti:
            if full:
                header2.append(alg + '.' + arg_display[q])
            else:
                header2.append(arg_display[q])
            for l in range(0, quanti - 1):
                header2.append("")
    righe.append(header2)

    header3 = ['']
    for alg in trovati:
        for q in richiesti:
            if args.mean: header3.append("Average")
            if args.median: header3.append("Median")
            if stddev: header3.append("Standard deviation")
            if count_flag: header3.append("Count")
            if args.min: header3.append("Minimum")
            if args.max: header3.append("Maximum")
    if quanti > 1:
        righe.append(header3)

    # helper per estrarre dalla tabella pivotata
    def get_from_pivot(typ, dr, q, metric):
        try:
            # pivoted[metric][dr][q] if metric is first level
            val = pivoted[(metric, dr, q)].get(typ) if (metric, dr, q) in pivoted.columns else None
        except Exception:
            val = None
        if val is None or (hasattr(val, 'item') and pd.isna(val)):
            return ""
        # val può essere numpy scalar
        try:
            return float(val)
        except Exception:
            return ""

    def excel_col_letter(col_idx_one_based):
        # Convert 1-based column index to Excel column letter.
        letters = []
        while col_idx_one_based > 0:
            col_idx_one_based, rem = divmod(col_idx_one_based - 1, 26)
            letters.append(chr(65 + rem))
        return ''.join(reversed(letters))

    for typ in types_list:
        row = [typ]
        toPrint = False
        missing_by_alg = {alg: False for alg in trovati}

        for dr in trovati:
            for q in richiesti:
                for metric in order_metrics:
                    # metric names in pivot are the same strings (mean, median, std, count, min, max)
                    try:
                        # pivoted columns are MultiIndex (metric, dir, arg)
                        if (metric, dr, q) in pivoted.columns:
                            val = pivoted[(metric, dr, q)].get(typ)
                        else:
                            val = None
                    except Exception:
                        val = None

                    if val is None or (hasattr(val, 'item') and pd.isna(val)):
                        missing_by_alg[dr] = True
                        if metric == 'count':
                            row.append(0)
                        else:
                            row.append("")
                    else:
                        # normalizza count come int
                        if metric == 'count':
                            row.append(int(val))
                        else:
                            try:
                                row.append(float(val))
                            except Exception:
                                row.append("")
                        toPrint = True

        if complete and any(missing_by_alg.values()):
            continue

        if empty or toPrint:
            toWrite = True
            if grep:
                if not re.search(grep, typ):
                    toWrite = False
                if grep_invert:
                    toWrite = not toWrite

            if toWrite:
                righe.append(row)

    # scrivi CSV su stdout oppure su file
    out_lines = []
    if len(righe) > 2:
        for row in righe:
            out_lines.append(','.join(map(str, round_floats(row, args.digits))))

    formula_results = {}
    # optionally compute column means and append as last CSV row
    if args.columnMean and len(out_lines) > 0:
        # determine number of header rows at start of righe
        header_count = 0
        for r in righe:
            if len(r) == 0:
                header_count += 1
                continue
            if r[0] in ('', 'instance'):
                header_count += 1
                continue
            break
        # number of columns from first data row (after headers)
        if header_count < len(righe):
            num_cols = len(righe[header_count])
            means = ["MEAN"]  # first column label
            for c in range(1, num_cols):
                vals = []
                for data_row in righe[header_count:]:
                    if c < len(data_row):
                        v = data_row[c]
                        try:
                            vals.append(float(v))
                        except Exception:
                            pass
                if vals:
                    means.append(np.mean(vals))
                else:
                    means.append("")

            gap_vals = None
            if args.gap:
                gap_vals = ["GAP"]
                block_size = len(richiesti) * len(order_metrics)
                for c in range(1, num_cols):
                    if c <= block_size:
                        gap_vals.append("")
                        continue
                    base_idx = 1 + ((c - 1) % block_size)
                    try:
                        base_val = float(means[base_idx])
                        cur_val = float(means[c])
                    except Exception:
                        gap_vals.append("")
                        continue
                    if base_val == 0:
                        gap_vals.append("")
                    else:
                        gap_vals.append(((cur_val - base_val) / base_val) * 100.0)

            out_lines.append('')
            out_lines.append(','.join(map(str, round_floats(means, args.digits))))
            if gap_vals is not None:
                out_lines.append(','.join(map(str, round_floats(gap_vals, args.digits))))

            if out_path is None:
                righe.append([""] * num_cols)
                righe.append(means)
                if gap_vals is not None:
                    righe.append(gap_vals)
            else:
                data_start_row = header_count + 1
                data_end_row = len(righe)
                righe.append([""] * num_cols)
                mean_row_idx = len(righe) + 1
                means_excel = ['MEAN']
                for c in range(1, num_cols):
                    col_letter = excel_col_letter(c + 1)
                    # IFERROR keeps columns with no numeric data blank.
                    means_excel.append(
                        f'=IFERROR(AVERAGE({col_letter}{data_start_row}:{col_letter}{data_end_row}),"")'
                    )
                    formula_results[f'{col_letter}{mean_row_idx}'] = means[c]
                righe.append(means_excel)
                if gap_vals is not None:
                    gap_row_idx = len(righe) + 1
                    gap_excel = ['GAP']
                    for c in range(1, num_cols):
                        if c <= block_size:
                            gap_excel.append('')
                            continue
                        base_idx = 1 + ((c - 1) % block_size)
                        base_cell = f'{excel_col_letter(base_idx + 1)}{mean_row_idx}'
                        current_cell = f'{excel_col_letter(c + 1)}{mean_row_idx}'
                        gap_excel.append(
                            f'=IFERROR(IF(OR({base_cell}=0,{base_cell}="",{current_cell}=""),"",'
                            f'({current_cell}-{base_cell})/{base_cell}),"")'
                        )
                        result = gap_vals[c]
                        formula_results[f'{excel_col_letter(c + 1)}{gap_row_idx}'] = (
                            result / 100.0 if result != '' else ''
                        )
                    righe.append(gap_excel)
    if out_path is None:
        for ln in out_lines:
            print(ln)
    else:
        out_args = args.out
        out_path = out_args[0]
        df_out = pd.DataFrame(righe)
        num_fmt = "0" if args.digits <= 0 else "0." + ("0" * args.digits)
        pct_fmt = "0" if args.digits <= 0 else "0." + ("0" * args.digits) + "%"

        try:
            previous_formula_results = (
                read_excel_formula_results(out_path) if engine == 'openpyxl' and mode == 'a' else {}
            )
            with pd.ExcelWriter(out_path, engine=engine, mode=mode, if_sheet_exists=if_sheet_exists) as writer:
                df_out.to_excel(writer, index=False, header=False, sheet_name=sheet_to_use)
                if engine == "xlsxwriter":
                    workbook = writer.book
                    worksheet = writer.sheets[sheet_to_use]
                    fmt = workbook.add_format({"num_format": num_fmt})
                    if df_out.shape[1] > 1:
                        worksheet.set_column(1, df_out.shape[1] - 1, None, fmt)
                    if args.columnMean:
                        mean_row_idx = df_out.shape[0] - (1 if args.gap else 0)  # 1-based row index
                        worksheet.set_row(mean_row_idx - 1, None, fmt)
                    if args.gap:
                        gap_row_idx = df_out.shape[0]  # 1-based row index in Excel
                        gap_fmt = workbook.add_format({"num_format": pct_fmt})
                        worksheet.set_row(gap_row_idx - 1, None, gap_fmt)
                    for reference, result in formula_results.items():
                        match = re.fullmatch(r'([A-Z]+)(\d+)', reference)
                        row_idx = int(match.group(2)) - 1
                        col_idx = 0
                        for letter in match.group(1):
                            col_idx = col_idx * 26 + ord(letter) - ord('A') + 1
                        worksheet.write_formula(
                            reference, righe[row_idx][col_idx - 1],
                            gap_fmt if args.gap and row_idx == gap_row_idx - 1 else fmt,
                            result,
                        )
                    workbook.set_calc_mode('auto')
                elif engine == "openpyxl":
                    ws = writer.sheets.get(sheet_to_use) or writer.book[sheet_to_use]
                    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=2, max_col=ws.max_column):
                        for cell in row:
                            if isinstance(cell.value, (int, float, np.number)):
                                cell.number_format = num_fmt
                    if args.columnMean and ws.max_row >= 1:
                        mean_row_idx = ws.max_row - (1 if args.gap else 0)
                        for cell in ws[mean_row_idx][1:]:
                            if cell.value is not None:
                                cell.number_format = num_fmt
                    if args.gap and ws.max_row >= 1:
                        gap_row_idx = ws.max_row
                        for cell in ws[gap_row_idx][1:]:
                            if cell.value is not None:
                                cell.number_format = pct_fmt
                    from openpyxl.workbook.properties import CalcProperties
                    writer.book.calculation = CalcProperties(
                        calcMode='auto', fullCalcOnLoad=True, forceFullCalc=True,
                    )
            if engine == 'openpyxl':
                for previous_sheet, cached in previous_formula_results.items():
                    if previous_sheet != sheet_to_use:
                        cache_excel_formula_results(out_path, previous_sheet, cached)
                cache_excel_formula_results(out_path, sheet_to_use, formula_results)
        except Exception as e:
            sys.exit(f"Failed to save Excel: {e}")


if __name__ == "__main__":
    main()
