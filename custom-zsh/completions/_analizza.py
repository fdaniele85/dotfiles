#compdef analizza.py analizza

_analizza() {
    _arguments -s -S \
        '(--empty --complete)--empty[Print rows with empty values]' \
        '(--empty --complete)--complete[Print only rows with values for all algorithms]' \
        '*--arguments=[objectpath expression for value extraction]:expr: ' \
        '--best-by=[Select the best run per instance using this objectpath expression]:expr: ' \
        '--solution=[Objectpath expression to print alongside --best-by]:expr: ' \
        '(-o --out)'{-o,--out}'[Output file (.xlsx/.xls) and optional sheet name]:file:_files' \
        '--type=[Filename regex to extract instance name]:regex: ' \
        '--replace=[Replacement string for --type regex]:string: ' \
        '(-g --grep)'{-g,--grep}'[Filter instances by regex]:pattern: ' \
        '-v[Invert --grep filter]' \
        '--onlyOne[Print one JSON file and exit]' \
        '--stddev[Include standard deviation]' \
        '--median[Include median]' \
        '--mean[Include mean]' \
        '--min[Include minimum]' \
        '--max[Include maximum (or: with --best-by, select the largest value)]' \
        '--count[Include count]' \
        '(-n --names)*'{-n,--names}'[Algorithm display names (one per input dir)]:name: ' \
        '*--column-names=[Column display names (one per --arguments value)]:name: ' \
        '--check=[Skip file if objectpath expr is falsy]:expr: ' \
        '--full[Use alg.arg format in column headers]' \
        '--size=[Skip file if objectpath array has size 0]:expr: ' \
        '--to-parquet=[Save raw extracted records to parquet file]:file:_files' \
        '--columnMean[Append column means row]' \
        '--gap[Append gap row after means (implies --columnMean)]' \
        '--digits=[Decimal digits for float output (default\: 2)]:n: ' \
        '--first=[Keep best N runs\: ARG N \[min|max\]]:arg: ' \
        '--silent[Suppress per-file stderr logging]' \
        '*:input directory:_directories'
}
_analizza "$@"
