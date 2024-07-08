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

      newid = cc.iam.new_group(grpname, desc)
      print('grp id', newid)
  elif argv[0] == 'del' or argv[0] == 'rm' or argv[0] == 'remove':
    try:
      grps = cc.iam.groups(argv[1])
      cc.iam.del_group(grps[0]['id'])
    except KeyError:
      print('Group already deleted')
  else:
    print('Usage')
    print('default : list groups')
    print('get group : get details for group')
    print('add grpname [descp: add new group')
    print('del grpname : del group')


