'''
## Tag recipes

These recipes are used to create and delete pre-defined tags.

## list

List currently pre-defined tags:

```bash
scullery tag
```

## add

Define pre-defined tags

```bash
scullery tag add key=value project=one project=two
```

## del

Delete pre-defined tags

```bash
scullery tag del key=value project=one project=two
```

***
'''
#
# TMS recipes
#
import argparse
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from scullery import cloud
from scullery import parsers

class C:
  ADD = '--add'
  DEL = '--del'
  MODE = 'mode'

def kvp_split(kvp:str) -> tuple[str,str]:
  '''INTERNAL: split key value pairs

  :param kvp: key value pair as a string of the form `key=value`
  :returns: a tuple split into key and value.
  '''
  if '=' in kvp:
    kk, vv = kvp.split('=',1)
  else:
    kk = kvp
    vv = kvp
  kk = kk.strip()
  vv = vv.strip()
  return kk,vv

def run(args:argparse.Namespace) -> None:
  '''Tag management (verbs: <none>, add, del)'''

  if args.mode is None:
    cc = cloud()
    for tag in cc.tms.tags():
      print(tag['key'],'=',tag['value'])
  elif args.mode == C.ADD:
    if not len(args.kvp):
      sys.stderr.write('Error: No key value pairs specified\n')
      exit(72)
    cc = cloud()
    for kvp in args.kvp:
      kk,vv = kvp_split(kvp)
      cc.tms.create(kk,vv)
  elif args.mode == C.DEL:
    if not len(args.kvp):
      sys.stderr.write('Error: No key value pairs specified\n')
      exit(72)
    cc = cloud()
    for kvp in args.kvp:
      kk,vv = kvp_split(kvp)
      cc.tms.delete(kk,vv)
  else:
    raise RuntimeError('Un-implemented mode')


def parser(subp):
  pr = subp.add_parser('tags',
                        help = 'Tag management service',
                        aliases = ['tms'])
  grp = pr.add_mutually_exclusive_group(required = False)
  grp.add_argument('-a', '--add',
                    dest = C.MODE,
                    help = 'Create a tag key=value pair',
                    action = 'store_const', const= C.ADD)
  grp.add_argument('-d', '--del',
                    dest = C.MODE,
                    help = 'Delete a tag key=value pair',
                    action = 'store_const', const= C.DEL)
  pr.add_argument('kvp',
                  help = 'Key value pair (key=value',
                  nargs='*')
  pr.set_defaults(recipe_cb = run, mode = None)


parsers.register_parser('tag management',parser)
