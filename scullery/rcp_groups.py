#
# Group recipe
#
'''
## Group recipes

Group recipe implementations

## list groups

List groups

```bash
scullery grp
```

## get group details

Get details related to a group.  This will show group definitions,
assigned domain roles and member users.

```bash
scullery grp get groupname
```

## add group

Create a new group

```bash
scullery grp add groupname [description]
```

## del group

Delete a group

```bash
scullery grp del groupname
```
***
'''

import json
import os
# ~ import sys
# ~ import yaml

from scullery import cloud

def run(argv:list[str]) -> None:
  '''Manage groups (verbs: <none>, get, add, del)'''
  cc = cloud()

  if len(argv) == 0:
    for g in cc.iam.groups():
      print('{name} {description}'.format(**g))
  elif argv[0] == 'get':
    for group_name in argv[1:]:
      group = cc.iam.groups(group_name)
      if len(group) != 1:
        print(f'{group_name} not matched')
        continue
      group = group[0]
      print('id:    {id}\n name: {name}\n desc: {description}'.format(**group))
      # ~ print(json.dumps(group,indent=2))

      perms = cc.iam.get_domain_group_perms(group['domain_id'], group['id'])
      if len(perms) > 0:
        # ~ print(json.dumps(perms,indent=2))
        print(' Domain roles:')
        for r in perms:
          print('  - {display_name}: {description}'.format(**r))

      users = cc.iam.group_users(group['id'])
      if len(users) > 0:
        print(' users;')
        for u in users:
          print('   {name}: {description}'.format(**u))

  elif argv[0] == 'add' or argv[0] == 'create' or argv[0] == 'new':
    if len(argv) >= 2:
      grpname = argv[1]
      desc = f'Group created by {os.getlogin()} using scullery' if len(argv) == 2 else argv[2]

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


