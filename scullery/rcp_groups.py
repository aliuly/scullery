#
# Roles recipe
#
import json
# ~ import sys
# ~ import yaml

from scullery import cloud

def run(argv:list[str]) -> None:
  cc = cloud()

  if len(argv) == 0:
    for g in cc.iam.groups():
      print('{name} {description}'.format(**g))
  elif argv[0] == 'get':
    for group_name in argv[1:]:
      group = cc.iam.groups(group_name)
      if len(group) != 1:
        print('{group_name} not matched')
        continue
      group = group[0]
      print('id:    {id}\n name: {name}\n desc: {description}\n users:'.format(**group))
      users = cc.iam.group_users(group['id'])
      for u in users:
        print('   {name}: {description}'.format(**u))
  elif argv[0] == 'add' or argv[0] == 'create' or argv[0] == 'new':
    if len(argv) >= 2:
      grpname = argv[1]
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
      role = cc.iam.get_role(argv[1])
      print(role)
      cc.iam.del_role(role['id'])
    except KeyError:
      print('Role already deleted')
  else:
    print('Usage')
    print('default : list custom roles')
    print('system : list system roles')
    print('get role : get details for role')
    print('add : add kermit role')
    print('del : del kermit role')


