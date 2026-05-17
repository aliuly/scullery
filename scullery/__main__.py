#!/usr/bin/env python3
''' Scullery command line

'''
import os
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from . import api
from . import parsers

from . import rcp_buckets
from . import rcp_cfgwiz
from . import rcp_deh
from . import rcp_ecs
from . import rcp_groups
from . import rcp_ims
from . import rcp_login
from . import rcp_projects
from . import rcp_rms
from . import rcp_roles
from . import rcp_tms
from . import rcp_users

# ~ from . import proxycfg
# ~ from . import rcp_showcfg

def main(argv:list[str]) -> None:
  '''Main script entry point

  :param argv: Command line arguments
  '''
  cli = parsers.parser_factory(color = True)
  args = cli.parse_args(argv)

  if args.debug: api.http_logging()
  # ~ if args.cloud is not None: scullery.defaults['cloud'] = args.cloud

  if not hasattr(args,'recipe_cb'):
    cli.print_help()
  else:
    args.recipe_cb(args)


###################################################################
#
# Main command line
#
###################################################################

if __name__ == '__main__':
  main(sys.argv[1:])
