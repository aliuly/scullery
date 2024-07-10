#!/bin/sh
#
# Run python using venv
#
mydir=$(dirname "$0")
export PYTHONPATH="$mydir:$PYTHONPATH"
exec "$mydir/pys" -m scullery -I"$mydir/recipes" "$@"

