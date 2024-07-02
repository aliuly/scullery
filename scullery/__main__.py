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
import scullery.proxycfg as proxycfg
import string
import ypp.pwhash

from scullery import cloud

def cmd_cli():
  ''' Command Line Interface argument parser '''
  cli = ArgumentParser(prog=scullery.__meta__.name,description=scullery.__meta__.description)
  
  grp1 = cli.add_argument_group('Pre-processor options')
  grp1.add_argument('-D','--define', help='Add constant', action='append', default=[])
  grp1.add_argument('-I','--include', help='Add Include path', action='append', default=[])
  grp1.add_argument('-C','--config', help='Read configuration file', action='append', default=[])
  
  cli.add_argument('-V','--version', action='version', version='%(prog)s '+ scullery.VERSION)
  cli.add_argument('-A','--autocfg',help='Use WinReg to configure proxy', action='store_true', default = False)
  cli.set_defaults(excmd = None)

  grp1 = cli.add_argument_group('Sub command options')
  grp1.add_argument('--showproxy', help = 'Show proxy configuration (Use -Ddebug for more info)',
                  dest = 'excmd', action='store_const', const = K.SHOWPROXY)
  grp1.add_argument('--pwgen', help='Generate passwords (Use -Dpwlen=num, -Dupper, -Dlower -Ddigits, -Dn=count)',
                  dest = 'excmd', action='store_const', const = 'pwgen')

  cli.add_argument('recipe', help='Recipe(s) to run', nargs='*')
  return cli

def run_recipe(txt:str) -> None:
  exec(txt)

def main(argv:list[str]) -> None:
  cli = cmd_cli()
  args = cli.parse_args(argv)
  ic(args)
  if args.excmd is None:
    if len(args.recipe) == 0:
      sys.stderr.write('No recipes specified\n')
      sys.exit(0)
    if args.autocfg: proxycfg.proxy_cfg()

    ypp.init(args.config, args.include, args.define, {
        K.CLOUD: K.DEFAULT_CLOUD_NAME,
      }, '')
    for recipe in args.recipe:
      sys.stderr.write(f'Running {recipe}\n')
      txt= ypp.process(recipe)
      run_recipe(txt)
  elif args.excmd == K.SHOWPROXY:
    debug = True if K.DEBUG in args.define else False
    if args.autocfg:
      proxy, url, jstext = proxycfg.proxy_auto_cfg()
      print(f'Auto config URL: {url}')
      print(f'Proxy: {proxy}')
      if debug: print(f'Javascript:\n{jstext}')
    else:
      print('No proxy autoconfiguration')
      if 'http_proxy' in os.environ: print('http_proxy:  {http_proxy}'.format(http_proxy=os.environ['http_proxy']))
      if 'https_proxy' in os.environ: print('https_proxy: {https_proxy}'.format(https_proxy=os.environ['https_proxy']))
  elif args.excmd == K.PWGEN:
    pwlen = 8
    chrset = ''
    count = 8
    for opts in args.define:
      if opts.lower() == K.UPPER:
        chrset += string.ascii_uppercase
      elif opts.lower() == K.LOWER:
        chrset += string.ascii_lowercase
      elif opts.lower() == K.DIGITS:
        chrset += string.digits
      elif opts.lower().startswith(K.PWLEN + '='):
        pwlen = int(opts[len(K.PWLEN)+1:])
      elif opts.lower().startswith('n='):
        count = int(opts[2:])
    if chrset == '': chrset = string.ascii_uppercase + string.ascii_lowercase + string.digits
    for i in range(count):
      print(ypp.pwhash.gen_rand(pwlen, chrset))
    
    
###################################################################
#
# Main command line
#
###################################################################

if __name__ == '__main__':
  main(sys.argv[1:])
