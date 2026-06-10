#!/usr/bin/env python3
''' Scullery command line

'''
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from . import api
from . import parsers
from . import proxycfg

from . import rcp_agencies   # noqa: F401
from . import rcp_buckets   # noqa: F401
from . import rcp_cfgwiz    # noqa: F401
from . import rcp_deh       # noqa: F401
from . import rcp_ecs       # noqa: F401
from . import rcp_groups    # noqa: F401
from . import rcp_ims       # noqa: F401
from . import rcp_kms       # noqa: F401
from . import rcp_login     # noqa: F401
from . import rcp_obs       # noqa: F401
from . import rcp_projects  # noqa: F401
from . import rcp_rms       # noqa: F401
from . import rcp_roles     # noqa: F401
from . import rcp_tms       # noqa: F401
from . import rcp_users     # noqa: F401

if sys.platform == "win32":
  from . import rcp_showcfg # noqa: F401


def main(argv:list[str]|None = None) -> None:
  '''Main script entry point

  :param argv: Command line arguments
  '''
  if argv is None: argv = sys.argv[1:]

  cli = parsers.parser_factory(color = True)
  args = cli.parse_args(argv)

  if sys.platform == "win32" and hasattr(args,'autocfg') and getattr(args,'autocfg'):
    proxycfg.proxy_cfg(True)

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
