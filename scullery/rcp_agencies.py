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
  prjs = None

  for ag in data:
    if prjs is None: prjs = cc.iam.projects()
    if p := cc.iam.agency_domain_perms(ag['id']): ag['domain_perms'] = p
    pp = dict()
    if p:= cc.iam.agency_project_perms(ag['id'], None): pp[''] = p
    for prj in prjs:
      if p := cc.iam.agency_project_perms(ag['id'], prj['id']):
        if not args.all:
          for i in p:
            # Summarize...
            del i['policy'], i['domain_id'], i['description_cn'], i['catalog'], i['id'], i['type']
          pp[prj['name']] = p
        else:
          pp[prj['id']] = {
            'name': prj['name'],
            'roles': p,
          }
    if pp: ag['project_perms'] = pp
  
    formatters.write_single_output(ag, args.format)

def add_agency(args: argparse.Namespace) -> None:
  '''Create new agency'''
  ic(args)
  cc = clouds.session(args)

  cc.iam.new_agency(
        name = args.name,
        trust_domain = args.trust_domain,
        description = args.description,
        duration = args.duration,
    )
  

def del_agency(args: argparse.Namespace) -> None:
  '''Delete agency'''
  ic(args)
  cc = clouds.session(args)
  for n in args.name:
    ag_id = cc.iam.agencies(name = n)[0]['id']
    cc.iam.del_agency(ag_id)


def resolve_roles(cc, role_name) -> str:
  for r in cc.iam.system_roles():
    if r['name'] == role_name: return r['id']
  for r in cc.iam.custom_roles():
    if r['name'] == role_name: return r['id']
  raise KeyError(f'{role_name}: role not found')  
  
  
def grant_agency(args: argparse.NameSpace) -> None:
  '''Grant agency'''
  ic(args)
  cc = clouds.session(args)
  q = cc.iam.agencies(name = args.agency)
  if len(q) != 1: raise KeyError(f'{args.agency}: not found')
  ag_id = q[0]['id']
  role_id = resolve_roles(cc, args.role)
  if args.target is None:
    cc.iam.agency_grant_project(ag_id, role_id)
  elif args.target == '--domain':
    # Domain perms
    cc.iam.agency_grant_domain(ag_id, role_id)
  else:
    q = cc.iam.projects(name = args.target)
    if len(q) != 1: raise KeyError(f'{args.target}: project error')
    prj_id = q[0]['id']
    cc.iam.agency_grant_project(ag_id, role_id, prj_id)

  
def revoke_agency(args: argparse.NameSpace) -> None:
  '''Revoke agency'''
  ic(args)
  cc = clouds.session(args)
  q = cc.iam.agencies(name = args.agency)
  if len(q) != 1: raise KeyError(f'{args.agency}: not found')
  ag_id = q[0]['id']
  role_id = resolve_roles(cc, args.role)
  if args.target is None:
    cc.iam.agency_revoke_project(ag_id, role_id)
  elif args.target == '--domain':
    # Domain perms
    cc.iam.agency_revoke_domain(ag_id, role_id)
  else:
    q = cc.iam.projects(name = args.target)
    if len(q) != 1: raise KeyError(f'{args.target}: project error')
    prj_id = q[0]['id']
    cc.iam.agency_revoke_project(ag_id, role_id, prj_id)

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
  sp = pr.add_subparsers(title='op',
                          description='Operation.  If not specified, list agencies.',
                          required = False,
                          help = 'Operation')
  pp = sp.add_parser('get',
      help = 'Get details for agency',
  )
  pp.add_argument('-a','--all',
                  help='Include all details',
                  action = 'store_true',
                  default = False,
                  )
  pp.add_argument('agency',
                  help='Agency to look-up',
                  nargs='+')
  pp.set_defaults(recipe_cb = get_agency)
  formatters.add_single_format_arg(pp)

  pp = sp.add_parser('add',
                  help = 'Add agency',
                  aliases = ['new','create'])
  pp.set_defaults(recipe_cb = add_agency)

  pp.add_argument('-d','--description','--desc', dest = 'description',
                  help = 'Description for this agency')
  pp.add_argument('-D','--duration', dest='duration',
                  help = 'Duration for this agency',
                  default = None, choices = [ 'FOREVER', 'ONEDAY'],
  )                  
  pp.add_argument('name',
                help = 'Agency name')
  pp.add_argument('trust_domain',
                help = 'Trust Domain name')


  pp = sp.add_parser('del',
                  help = 'Delete agency',
                  aliases = ['rm'])
  pp.set_defaults(recipe_cb = del_agency)
  pp.add_argument('name',
                  nargs='+',
                  help='agency to delete')


  pp = sp.add_parser('grant',
                  help = 'Grant permissions to an agency',
                  aliases = ['gr'])
  pp.set_defaults(recipe_cb = grant_agency)
  pp.add_argument('agency',
                  help='agency to grant priviledges to')
  pp.add_argument('role',
                  help='role or permissions to grant')
  pp.add_argument('target',
                  help='Object to grant permissions on, either project name, --domain or omit for inherit permissions',
                  nargs='?',
                  default = None)
                  
  pp = sp.add_parser('revoke',
                  help = 'Revoke permissions from an agency',
                  aliases = ['rvk'])
  pp.set_defaults(recipe_cb = revoke_agency)
  pp.add_argument('agency',
                  help='agency to revoke priviledges from')
  pp.add_argument('role',
                  help='role or permissions to revoke')
  pp.add_argument('target',
                  help='Object to revoke permissions from, either project name, --domain or omit for inherit permissions',
                  nargs='?',
                  default = None)



parsers.register_parser('agency',parser)
