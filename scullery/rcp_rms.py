#
# RMS recipes
#
from scullery import cloud

def run(argv:list[str]) -> None:
  '''Resource management'''
  cc = cloud()

  if len(argv) == 0:
    args = []
  else:
    args = [ argv[0] ]

  for rs in cc.rms.resources(*args):
    print('{provider}.{type} {name} {project_name}'.format(**rs))
    # ~ print(rs)
