'''
Used to define sub-parsers
'''
import argparse
import sys
from typing import Callable

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from . import __meta__

PARSER_FACTORY = {}

def register_parser(mid:str, parser_cb:Callable[None,[argparse.Namespace]]) -> None:
  '''Register a sub-parser

  :param mid: id for this sub-parser... Mainly used for sorting
  :param parser_cb: callback function that registers a sub-parser
  '''
  PARSER_FACTORY[mid] = parser_cb

def parser_factory(color:bool = False) -> argparse.ArgumentParser:
  ''' Command Line Interface argument parser

  :param color: optional color support flag
  :returns: Configured argparse.ArgumentParser
  '''
  color = { 'color': color } if sys.version_info >= (3,14) else dict()
  cli = argparse.ArgumentParser(
                        prog=__meta__.name,
                        description=__meta__.description,
                        allow_abbrev = True,
                        **color,
                      )
  cli.add_argument('-V','--version',
      action='version',
      version='%(prog)s '+ __meta__.version,
  )
  cli.add_argument('-d', '--debug',
      help='Turn on debugging options',
      action='store_true',
      default = False,
  )
  if sys.platform == 'win32':
    cli.add_argument('--autocfg','-A',
        help='Use WinReg to configure proxy',
        action='store_true',
        default = False,
    )
  sgrp = cli.add_argument_group(
      title= 'Scoping',
      description = 'Define scoped/unscoped recipes',
  )

  xscope = sgrp.add_mutually_exclusive_group()
  xscope.add_argument('--project','-p',
      help='Specify Project for project scoped recipes',
      default = None,
  )
  xscope.add_argument('--region','-R',
      help='Specify region to use for unscopped recipes',
      default = None,
  )

  atgrp = cli.add_argument_group(
      title = 'Authentication options',
      description = 'Type of authentication to use'
  )
  xagrp = atgrp.add_mutually_exclusive_group()
  xagrp.add_argument('--token',
      help='Token to use (or environment OS_AUTH_TOKEN or OS_TOKEN)',
      default = None,
  )
  xagrp.add_argument('--ak',
      help='Access Key for AK/SK authentication (or environment OS_ACCESS_KEY)',
      default = None,
  )
  xagrp.add_argument('--username','-u',
      help = 'Username for username+password authentication (or environment OS_USERNAME)',
      default = None,
  )

  akskgrp = cli.add_argument_group(
      title = 'AK/SK authentication',
      description = 'Options specific to AK/SK authentication',
  )
  akskgrp.add_argument('--sk',
      help='Secret Key for AK/SK authentication (or environment OS_SECRET_KEY)',
      default = None,
  )
  akskgrp.add_argument('--security-token','--security_token', '--securitytoken',
      dest = 'securitytoken',
      help='Security token for temp AK/SK authentication (or environment OS_SECURITY_TOKEN)',
      default = None,
  )

  ugrp = cli.add_argument_group(
      title = 'Username+password authentication',
      description  = 'Options related to username+password authentication',
  )
  ugrp.add_argument('--password', '--passwd','-P',
      help = 'Password for username+password authentication (or environment OS_PASSWORD)',
      default = None,
  )
  ugrp.add_argument('--user-domain','--user_domain','--userdomain',
      dest = 'user_domain_name',
      help = 'User domain (OTC0000XXXX for username+password authentication (or environment OS_USER_DOMAIN_NAME)',
      default = None,
  )


  subp = cli.add_subparsers(
                    title ='recipe',
                    description = 'Recipe to execute',
                    required = False,
                    help = 'Run a recipe')
  for _, fact in sorted(PARSER_FACTORY.items()):
    fact(subp)

  return cli

def sphinxarg_common(text:str, parser:Callable[None,[argparse.ArgumentParser]]) -> argparse.ArgumentParser:
  color = { 'color': False } if sys.version_info >= (3,14) else dict()
  tmp = argparse.ArgumentParser(prog = 'RECIPE',
                        description = text,
                        **color,
                      )
  parser(tmp.add_subparsers(title='recipe', help='Recipe to run'))
  return tmp
