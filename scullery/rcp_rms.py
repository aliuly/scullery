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

from scullery import cloud

def run(argv:list[str]) -> None:
  '''Resource management (specify a project to limit list)'''
  cc = cloud()

  if len(argv) == 0:
    args = []
  else:
    args = [ argv[0] ]

  for rs in cc.rms.resources(*args):
    print('{provider}.{type} {name} {project_name}'.format(**rs))
    # ~ print(rs)
