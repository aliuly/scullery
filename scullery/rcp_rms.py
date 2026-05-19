#
# RMS recipes
#
'''
Resource management recipes

This recipe is used to list resources optionally filtered by
_projectname_.

If no `projectname` is specified it should list all resources.  If
`projectname` is specified it will list all resources related
to the given project.

Output format can be controlled with `-f` / `--format`:

| Format       | Description                         |
|--------------|-------------------------------------|
| `terminal` | Aligned columns for your terminal   |
| `json`     | JSON array of resources             |
| `csv`      | Comma-separated values              |
| `tsv`      | Tab-separated values                |
| `markdown` | Markdown / pipe table               |


'''

import argparse
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from . import clouds
from . import formatters
from . import parsers


# Ordered list of (dict_key, column_label) pairs shown in the output.
COLUMNS: formatters.Columns = [
  ('project_name', 'Project'),
  ('provider',     'Provider'),
  ('type',         'Type'),
  ('name',         'Name'),
  ('region_id',    'Region'),
]


def run(args: argparse.Namespace) -> None:
  '''Resource management (specify a project to limit list)'''
  if args.project is not None:
    args.region = args.project.split('_')[0]
    if args.prjmatch is None: args.prjmatch = args.project
    args.project = None

  cc = clouds.session(args)
  resources = cc.rms.resources(args.prjmatch, args.type)
  rows = formatters.extract_rows(resources, COLUMNS)
  formatters.write_output(rows, COLUMNS, args.format)

def sphinxarg() -> argparse.ArgumentParser:
  return parsers.sphinxarg_common(
        sys.modules[__name__].__doc__,
        parser,
  )


def parser(subp: argparse.ArgumentParser) -> None:
  '''Register the ``resources`` sub-parser'''
  pr = subp.add_parser('rms',
                       help='Resource management',
                     )
  pr.add_argument('-m', '--project',
                  dest = 'prjmatch',
                  help='Match project (or region)',
                  default=None)
  pr.add_argument('-T','--tags',
                help='Spcifies tags, format is *key* or *key=value*',
                action = 'append',
                default = [],
  )
  pr.add_argument('-t', '--type',
                  help='Resource type in the format *provider.type*',
                  default=None)
  formatters.add_format_arg(pr)
  pr.set_defaults(recipe_cb=run)


parsers.register_parser('resources', parser)



