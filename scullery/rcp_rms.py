#
# RMS recipes
#
'''Resource management implementation'''

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
