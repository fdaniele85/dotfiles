#compdef testa.py

_arguments \
  "(- :)"{-h,--help}"[show this help message and exit]" \
  "--alg[Algorithm]:alg:_files" \
  "--res[Results dir]:res:_dirs" \
  "--ins[Input dir or file]:ins:_files" \
  "--thread[Number of threads]:thread:( )" \
  "--seeds[Seeds]:seeds:( )" \
  "--ext[Extension]:ext:( )" \
  "--noseed[No seed]" \
  "--time[Max time in seconds]:time:( )" \
  "--log[Log prefix]:log:( )"