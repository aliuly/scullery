#!/usr/bin/env python3
''' Scullery command line

'''
import os
import sys

from argparse import ArgumentParser

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

if '__file__' in globals():
  sys.path.append(os.path.join(os.path.dirname(__file__),'..'))

import scullery
import scullery.proxycfg as proxycfg

import scullery.rcp_groups as rcp_groups
import scullery.rcp_kermit as rcp_kermit
import scullery.rcp_projects as rcp_projects
import scullery.rcp_rms as rcp_rms
import scullery.rcp_roles as rcp_roles
import scullery.rcp_tms as rcp_tms
import scullery.rcp_users as rcp_users


from scullery import cloud

SHOWPROXY = 'showproxy'
BUILTINS = 'builtins'
DISPATCH_TABLE = dict()
'''Command dispatch table'''

DISPATCH_TABLE['group'] = rcp_groups.run
DISPATCH_TABLE['grp'] = rcp_groups.run
DISPATCH_TABLE['kermit'] = rcp_kermit.run
DISPATCH_TABLE['prj'] = rcp_projects.run
DISPATCH_TABLE['project'] = rcp_projects.run
DISPATCH_TABLE['rms'] = rcp_rms.run
DISPATCH_TABLE['role'] = rcp_roles.run
DISPATCH_TABLE['tag'] = rcp_tms.run
DISPATCH_TABLE['tms'] = rcp_tms.run
DISPATCH_TABLE['user'] = rcp_users.run
DISPATCH_TABLE['usr'] = rcp_users.run

def cmd_cli():
  ''' Command Line Interface argument parser '''
  cli = ArgumentParser(prog=scullery.__meta__.name,description=scullery.__meta__.description)

  cli.add_argument('-A','--autocfg',help='Use WinReg to configure proxy', action='store_true', default = False)
  cli.add_argument('-C','--cloud', help='Specify default cloud config')
  cli.add_argument('-I','--include', help='Add Include path', action='append', default=[  ])
  cli.add_argument('-V','--version', action='version', version='%(prog)s '+ scullery.VERSION)
  cli.add_argument('-d', '--debug', help='Turn on debugging options', action='store_true', default = False)
  cli.set_defaults(excmd = None)

  grp1 = cli.add_argument_group('Sub command options')
  grp1.add_argument('--showproxy', help = 'Show proxy configuration',
                  dest = 'excmd', action='store_const', const = SHOWPROXY)
  grp1.add_argument('--built-ins', help = 'List built-in recipes',
                  dest = 'excmd', action='store_const', const = BUILTINS)

  cli.add_argument('recipe', help='Recipe(s) to run', nargs='?')
  return cli

def run_recipe(recipe:str, argv:list[str], autocfg:bool = False, incpath:list[str] = []) -> None:
  '''Run a recipe

  :param recipe: Recipe to run
  :param argv: commandline arguments
  :param autocfg: Automatic proxy configuration
  :param incpath: Include path for searching recipes
  '''
  if autocfg: proxycfg.proxy_cfg()

  if recipe in DISPATCH_TABLE:
    DISPATCH_TABLE[recipe](argv)
  else:
    if not os.path.isfile(recipe):
      for incdir in incpath:
        if os.path.isfile(os.path.join(incdir, recipe + '.py')):
          recipe = os.path.join(incdir,recipe + '.py')
          break
    with open(recipe, 'r') as fp:
      txt = fp.read()
    sys.stderr.write(f'Running {recipe}\n')
    exec(txt)
  scullery.clean_up()

def show_proxy(autocfg:bool, debug:bool = False) -> None:
  '''Handle show proxy sub-command

  :param autocfg: Perform auto configuration
  :param debug: Show extra details
  '''
  if autocfg:
    proxy, url, jstext = proxycfg.proxy_auto_cfg()
    print(f'Auto config URL: {url}')
    print(f'Proxy: {proxy}')
    if debug: print(f'Javascript:\n{jstext}')
  else:
    print('No proxy autoconfiguration')
    if 'http_proxy' in os.environ: print('http_proxy:  {http_proxy}'.format(http_proxy=os.environ['http_proxy']))
    if 'https_proxy' in os.environ: print('https_proxy: {https_proxy}'.format(https_proxy=os.environ['https_proxy']))

def main(argv:list[str]) -> None:
  '''Main script entry point

  :param argv: Command line arguments
  '''
  cli = cmd_cli()
  args, script_args = cli.parse_known_args(argv)

  if not args.cloud is None: scullery.defaults['cloud'] = args.cloud

  if args.excmd is None:
    ic(args)
    if args.recipe is None:
      sys.stderr.write('Must specify one recipe\n')
      sys.exit(0)
    if args.debug: scullery.api.http_logging(2)
    run_recipe(args.recipe, script_args, args.autocfg, args.include)
  elif args.excmd == SHOWPROXY:
    show_proxy(args.autocfg, args.debug)
  elif args.excmd == BUILTINS:
    print('Built-in recipes')
    rcp_table = {}
    for name,callback in DISPATCH_TABLE.items():
      cbstr = str(callback)
      if not cbstr in rcp_table:
        rcp_table[cbstr] = {
          'recipe': [ name ],
          'help': callback.__doc__
        }
      else:
        rcp_table[cbstr]['recipe'].append(name)
    for t in rcp_table.values():
      if t['help'] is None:
        print(' - {}'.format(', '.join(t['recipe'])))
      else:
        print(' - {}: {}'.format(', '.join(t['recipe']), t['help']))


###################################################################
#
# Main command line
#
###################################################################

if __name__ == '__main__':
  main(sys.argv[1:])
