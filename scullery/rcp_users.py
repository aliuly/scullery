#
# Roles recipe
#
import json
import random
import string
import sys

from scullery import cloud

def run(argv:list[str]) -> None:
  cc = cloud()

  if len(argv) == 0:
    for u in cc.iam.users():
      if not 'description' in u: u['description'] = ''
      print('{name} {description} {email} {domain_id}'.format(**u))
  elif argv[0] == 'get':
    for user_name in argv[1:]:
      users = cc.iam.users(user_name)
      if len(users) != 1:
        print('{user_name} not matched')
        continue
      u = users[0]
      print(json.dumps(u,indent=2))
      q = cc.iam.user_groups(u['id'])
      if len(q) > 0:
        print('groups:')
        for g in q:
          print('  {name} {description}'.format(**g))
  elif argv[0] == 'add' or argv[0] == 'create' or argv[0] == 'new':
    domain_id = None
    for p in cc.iam.projects():
      domain_id = p['domain_id']
      break
    if domain_id is None:
      print('Unable to find a suitable domain ID')
      exit(1)

    groups = {}
    new_user = {
        'pwd_status': False,
        'domain_id': domain_id,
        'description': 'user created via API',
    }
    for opt in argv[1:]:
      found = False
      for arg in ['name','password','email','description']:
        if opt.startswith('--'+arg):
          new_user[arg] = opt[len(arg)+3:]
          found = True
          break
      if found: continue
      if opt.startswith('--group='):
        q = cc.iam.groups(opt[8:])
        if len(q) != 1:
          sys.stderr.write(f'Invalid group name {opt[8:]}\n')
          exit(9)
        groups[q[0]['name']] = q[0]['id']
    if not 'name' in new_user:
      new_user['name'] = ''.join(random.sample(string.ascii_lowercase*8,8))
      print('Random user name:', new_user['name'])
    if not 'password' in new_user:
      new_user['password'] = ''.join(random.sample((string.ascii_lowercase + string.ascii_uppercase + string.digits)*24, 24))
      print('Random password:', new_user['password'])

    # ~ print(new_user, groups)
    newid = cc.iam.new_user(**new_user)
    print('New user ID',newid)

    # name
    # password
    # email
    # pwd_status : False
    # description

      # ~ print(json.dumps(p,indent=2))
      # ~ details = cc.iam.get_project_details(p['id'])
    # ~ add
    # ~ name
    #

    # ~ if len(argv) >= 2:
      # ~ user_name = argv[1]
      # ~ desc = None if len(argv) == 2 else argv[2]

      # ~ newid = cc.iam.new_group(grpname, desc)
      # ~ print('grp id', newid)
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
    print('del grpname : del group')


