'''
Implement user related recipes
'''
#
# Roles recipe
#
import json
import os
import sys

from scullery import cloud

def run(argv:list[str]) -> None:
  '''Manage users (verbs: <none>, get, add, group, del)'''
  cc = cloud()

  if len(argv) == 0:
    for u in cc.iam.users():
      if not 'description' in u: u['description'] = ''
      print('{name} {description} {email}'.format(**u))
  elif argv[0] == 'get':
    for user_name in argv[1:]:
      users = cc.iam.users(user_name)
      if len(users) != 1:
        print(f'{user_name} not matched')
        continue
      u = users[0]
      print(json.dumps(u,indent=2))
      q = cc.iam.user_groups(u['id'])
      if len(q) > 0:
        print('groups:')
        for g in q:
          print('  {name} {description}'.format(**g))
  elif argv[0] == 'add' or argv[0] == 'create' or argv[0] == 'new':
    domain_id = cc.iam.domain()
    groups = {}
    new_user = {
        'pwd_status': False,
        'domain_id': domain_id,
        'description': f'user created by {os.getlogin()} using scullery',
    }
    for opt in argv[1:]:
      found = False
      for arg in ['name','password','email','description']:
        if opt.startswith('--'+arg):
          new_user[arg] = opt[len(arg)+3:]
          found = True
          break
      if found: continue
      if opt.startswith('--desc='):
        new_user['description'] = opt[7:]
      elif opt.startswith('--group='):
        q = cc.iam.groups(opt[8:])
        if len(q) != 1:
          sys.stderr.write(f'Invalid group name {opt[8:]}\n')
          exit(9)
        groups[q[0]['name']] = q[0]['id']
    if not 'name' in new_user:
      new_user['name'] = cc.iam.gen_user_name()
      print('Random user name:', new_user['name'])
    if not 'password' in new_user:
      new_user['password'] = cc.iam.gen_user_password()
      print('Random password:', new_user['password'])

    # ~ print(new_user, groups)
    newid = cc.iam.new_user(**new_user)
    print('New user ID',newid)
    for gname,gid in groups.items():
      print(f'Adding group {gname}')
      cc.iam.add_group_user(gid, newid)
  elif argv[0] == 'group':
    q = cc.iam.groups(argv[1])
    if len(q) != 1:
      print(f'Unmatched group {argv[1]}')
      exit(9)
    group = q[0]
    q = cc.iam.users(argv[3])
    if len(q) != 1:
      print(f'Unmatched user {argv[3]}')
      exit(4)
    user = q[0]
    if argv[2] == 'add':
      cc.iam.add_group_user(group['id'],user['id'])
    elif argv[2] == 'del' or argv[2] == 'rm' or argv[2] == 'remove':
      cc.iam.del_group_user(group['id'],user['id'])
    else:
      print(f'Unknown op {argv[2]}')
  elif argv[0] == 'del' or argv[0] == 'rm' or argv[0] == 'remove':
    q = cc.iam.users(argv[1])
    if len(q) != 1:
      print('User not matched')
      exit(2)
    cc.iam.del_user(q[0]['id'])
  else:
    print('Usage')
    print('default : list users')
    print('get usrname : get details for user')
    print('add --name= --password= --email= --description= --group=: add new user')
    print('del username : del user')
    print('group groupname add|del username : add or remove user from group')


