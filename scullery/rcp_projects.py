#
# Roles recipe
#
import json
import sys

from scullery import cloud

def run(argv:list[str]) -> None:
  cc = cloud()

  if len(argv) == 0:
    for p in cc.iam.projects():
      print('{id} {name:22} {description}'.format(**p))
  elif argv[0] == 'get':
    prjlst = cc.iam.projects(name=argv[1])
    for prj in prjlst:
      details = cc.iam.get_project_details(prj['id'])
      print(json.dumps(details, indent=2))
  elif argv[0] == 'add' or argv[0] == 'create' or argv[0] == 'new':
    print(len(argv))
    if len(argv) >= 2:
      prjname = argv[1]
      desc = None if len(argv) == 2 else argv[2]
      if not '_' in prjname:
        print('No region specified')
        return
      region, _ = prjname.split('_',1)
      regdat = cc.iam.projects(name=region)
      if len(regdat) != 1:
        print(f'Unknown region {region}')
        return

      newid = cc.iam.new_project(prjname, regdat[0]['id'], desc)
      print('prj id', newid)
    else:
      print('Usage: add <prjname> [description]')
  elif argv[0] == 'del' or argv[0] == 'rm' or argv[0] == 'remove':
    try:
      prjdat = cc.iam.projects(argv[1])
      if len(prjdat) != 1:
        print('Unable to find project')
        return
      cc.iam.del_project(prjdat[0]['id'])
    except KeyError:
      print('Project already deleted')
  else:
    print('Usage')
    print('default : list projects')
    print('get project prjname : get details for project')
    print('add prjname description : add project')
    print('del prjname: del kermit project -- make sure all resources are deleted before using this')


