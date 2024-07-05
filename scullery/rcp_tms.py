#
# TMS recipes
#
from scullery import cloud


def kvp_split(kvp:str) -> tuple[str,str]:
  kk, vv = kvp.split('=',1)
  kk = kk.strip()
  vv = vv.strip()
  return kk,vv

def run(argv:list[str]) -> None:
  cc = cloud()

  if len(argv) == 0:
    for tag in cc.tms.tags():
      print(tag['key'],'=',tag['value'])
  elif argv[0] == 'add' or argv[0] == 'create' or argv[0] == 'new':
    for kvp in argv[1:]:
      kk,vv = kvp_split(kvp)
      cc.tms.create(kk,vv)
  elif argv[0] == 'del' or argv[0] == 'rm' or argv[0] == 'remove':
    for kvp in argv[1:]:
      kk,vv = kvp_split(kvp)
      cc.tms.delete(kk,vv)
  else:
    print('Usage')
    print('add key=value ...')
    print('del key=value ...')