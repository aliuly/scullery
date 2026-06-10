'''

This module implements agency related recipes.  The following
verbs are recognized.

| recipe | descripiton |
|---|----|
|  | List agencies |

'''
#
# Agencies recipe
#
import argparse
import json

import sys
import yaml

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from . import parsers
from . import formatters
from . import clouds



# Columns for the list (default table) view.
COLUMNS: formatters.Columns = [
  ('name',        'Name'),
  ('description', 'Description'),
  ('trust_domain_name',       'Trust Domain'),
]

COLUMNS_ALL: formatters.Columns = [
  ('id',    'ID'),
  ('name',  'Name'),
  ('domain_id', 'Domain ID'),
  ('trust_domain_id', 'Trust Domain ID'),
  ('trust_domain_name', 'Trust Domain'),
  ('description', 'Description'),
  ('duration', 'Duration'),
  ('expire_time', 'Expires'),
  ('create_time', 'Created'),
    
]


def list_agencies(args: argparse.Namespace) -> None:
  '''List all agencies'''
  cc = clouds.session(args)
  data = cc.iam.agencies()

  human = args.format in ('terminal', 'markdown')
  if human:
    cols = COLUMNS
  else:
    cols = COLUMNS_ALL

  rows = formatters.extract_rows(data, cols)
  formatters.write_output(rows, cols, args.format)


def get_agency(args: argparse.Namespace) -> None:
  '''List all agencies'''
  cc = clouds.session(args)
  data = cc.iam.agencies(name = args.agency)

  for ag in data:
    formatters.write_single_output(ag, args.format)


def sphinxarg() -> argparse.ArgumentParser:
  return parsers.sphinxarg_common(
        sys.modules[__name__].__doc__,
        parser,
  )


def parser(subp: argparse.ArgumentParser) -> None:
  '''Register the ``agencies`` sub-parser'''
  pr = subp.add_parser('agency',
                        help = 'Agency recipes',
                        aliases = ['agencies'])
  pr.set_defaults(recipe_cb = list_agencies)
  formatters.add_format_arg(pr)
  usp = pr.add_subparsers(title='op',
                          description='Operation.  If not spcified, list agenciess.',
                          required = False,
                          help = 'Operation')
  pp = usp.add_parser('get',
      help = 'Get details for agency',
  )
  pp.add_argument('agency',
                  help='Agency to look-up',
                  nargs='+')
  pp.set_defaults(recipe_cb = get_agency)
  formatters.add_single_format_arg(pp)


parsers.register_parser('agency',parser)
