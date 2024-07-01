#!/usr/bin/env python3
''' Scullery command line

'''
import os
import sys

# ~ import typing
# ~ import yaml

from argparse import ArgumentParser

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

if '__file__' in globals():
  sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
import scullery
import ypp
import scullery.consts as K


def cmd_cli():
  ''' Command Line Interface argument parser '''
  cli = ArgumentParser(prog=scullery.__meta__.name,description=scullery.__meta__.description)
  cli.add_argument('-D','--define', help='Add constant', action='append', default=[])
  cli.add_argument('-I','--include', help='Add Include path', action='append', default=[])
  cli.add_argument('-C','--config', help='Read configuration file', action='append', default=[])
  cli.add_argument('-V','--version', action='version', version='%(prog)s '+ scullery.VERSION)

  cli.add_argument('recipe', help='Recipe(s) to run', nargs='*')
  return cli

def run_recipe(txt:str) -> None:
  exec(txt)

def main(argv:list[str]) -> None:
  cli = cmd_cli()
  args = cli.parse_args(argv)
  if len(args.recipe) == 0:
    sys.stderr.write('No recipes specified\n')
    sys.exit(0)
  ic(args)
  ypp.init(args.config, args.include, args.define, {
      K.CLOUD: K.DEFAULT_CLOUD_NAME,
    }, '')
  for recipe in args.recipe:
    sys.stderr.write(f'Running {recipe}\n')
    txt= ypp.process(recipe)
    run_recipe(txt)

###################################################################
#
# Main command line
#
###################################################################

if __name__ == '__main__':
  main(sys.argv[1:])
