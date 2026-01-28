#
# ECS recipes
#
'''
## ECS recipes

Includes some stuff for Dedicated hosts....
'''

import argparse
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from scullery import cloud
from scullery import parsers
from scullery import ecs


def list_servers(args:argparse.Namespace) -> None:
  params = dict()
  for kvp in args.query:
    if '=' not in kvp:
      raise SyntaxError(f'{kvp}: Must specify key=value pair')
    key, value = kvp.split('=',1)
    params[key] = value

  cc = cloud(scoped = True)
  for ecs in cc.ecs.servers(detail = True, **params):
    print('{name} {id} {status}'.format(**ecs))
    

def action(args:argparse.Namespace) -> None:
  cc = cloud(scoped = True)
  for ecs_name in args.server:
    q = cc.ecs.servers(name = ecs_name)
    if len(q) != 1: raise KeyError(ecs_name)
    if args.mode == 'start':
      action = ecs.ACTION.START
    elif args.mode == 'stop':
      action = ecs.ACTION.HARD_STOP if args.hard else ecs.ACTION.SOFT_STOP
    elif args.mode == 'reboot':
      action = ecs.ACTION.HARD_REBOOT if args.hard else ecs.ACTION.SOFT_REBOOT
    else:
      raise RuntimeError(f'Unknown mode: {mode}')
    cc.ecs.action(q[0]['id'], action)
    sys.stderr.write(f'{ecs_name} ({q[0]["id"]}) {"Hard " if args.hard else ""} {args.mode}\n')

def list_azs(args:argparse.Namespace) -> None:
  cc = cloud(scoped = True)
  # ~ ic(cc.ecs.availability_zones())
  for az,azdat in cc.ecs.availability_zones().items():
    print(az, '\tAvailable' if azdat['available'] else '\tNot Available')
  

def list_deh_types(args:argparse.Namespace) -> None:
  cc = cloud(scoped = True)
  
  azs = cc.ecs.availability_zones()
  for az in azs:        
    for deh_type in cc.deh.deh_types(az):
      print('{az} {host_type:12} {host_type_name}'.format(az = az, **deh_type))

def list_flavors(args:argparse.Namespace) -> None:
  params = dict()
  for kvp in args.query:
    if '=' not in kvp:
      raise SyntaxError(f'{kvp}: Must specify key=value pair')
    key, value = kvp.split('=',1)
    params[key] = value

  cc = cloud(scoped = True)
  for flavor in cc.ecs.flavors(**params):
    if flavor['name'] == flavor['id']:
      print('{name} ram:{ram} vcpu:{vcpus}'.format(**flavor))
    else:
      print('{name} {id} ram:{ram} vcpu:{vcpus}'.format(**flavor))

def parser(subp):
  pr = subp.add_parser('ecs',
            help = 'ECS management',
            aliases = ['vms', 'deh'])
  pr.set_defaults(recipe_cb = list_servers, query = [])
  sp = pr.add_subparsers(title = 'op',
                        description = 'Operation: default to list servers',
                        required = False,
                        help = 'Operation')
  pp = sp.add_parser('servers',
                      help = 'List ECS servers',
                      )
  pp.add_argument('query',
                  nargs = '*',
                  help = 'Query arguments')
  pp.set_defaults(recipe_cb = list_servers)

  pp = sp.add_parser('start',
                    help = 'Start server',
                    aliases = ['on'])
  pp.add_argument('server',
                  nargs = '+',
                  help = 'server(s) to start')
  pp.set_defaults(recipe_cb = action, hard=None, mode='start')

  pp = sp.add_parser('stop',
                    help = 'Stop server',
                    aliases = ['off'])
  gg = pp.add_mutually_exclusive_group()
  gg.add_argument('-s','--soft', dest='hard',
                  action='store_false', 
                  help = 'Graceful shutdown')
  gg.add_argument('-f','--hard', dest='hard',
                  action='store_true', 
                  help = 'Hard power off')
  pp.add_argument('server',
                  nargs = '+',
                  help = 'server(s) to start')
  pp.set_defaults(recipe_cb = action, hard = False, mode='stop')
  
  pp = sp.add_parser('reboot',
                    help = 'Reboot server',
                    )
  gg = pp.add_mutually_exclusive_group()
  gg.add_argument('-s','--soft', dest='hard',
                  action='store_false', 
                  help = 'Soft reboot')
  gg.add_argument('-f','--hard', dest='hard',
                  action='store_true', 
                  help = 'Hard reset')
  pp.add_argument('server',
                  nargs = '+',
                  help = 'server(s) to stop')
  pp.set_defaults(recipe_cb = action, hard = False, mode='reboot')
  
  pp = sp.add_parser('az',
                    help = 'List availability zones',
                    aliases = ['availability-zones'])
  pp.set_defaults(recipe_cb = list_azs)
  
  pp = sp.add_parser('flavors',
                    help = 'List flavors',
                    aliases = ['flavours','f'])
  pp.add_argument('query',
                  nargs = '*',
                  help = 'Query arguments')
  pp.set_defaults(recipe_cb = list_flavors)

  pp = sp.add_parser('types',
                    help = 'List dedicated host types',
                    aliases = ['deh-types','deh'])
  pp.set_defaults(recipe_cb = list_deh_types)

parsers.register_parser('ecs',parser)



