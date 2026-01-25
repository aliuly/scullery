#
# RMS recipes
#
'''
## Resource management recipes

This recipe is used to list resources

```bash
scullery rms [projectname]
```

If no `projectname` is specified it should list all resources.  If
`projectname` is specified it will list all resources related
to the given project.

***
'''

import argparse

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from scullery import cloud
from scullery import parsers


def run(args:argparse.Namespace) -> None:
  '''Resource management (specify a project to limit list)'''
  cc = cloud()

  for rs in cc.rms.resources(args.project, args.type):
    print('{project_name} {provider}.{type} {name}'.format(**rs))


def parser(subp):
  pr = subp.add_parser('resources',
            help = 'Resource management',
            aliases = ['rms', 'rsc'])
  pr.add_argument('-m','--project',
                  help = 'Match project',
                  default = None)
  pr.add_argument('-t','--type',
                  help = 'Resource type',
                  default = None)
  pr.set_defaults(recipe_cb = run)

parsers.register_parser('resources',parser)



