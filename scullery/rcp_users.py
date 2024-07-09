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
    for u in cc.iam.users():
      print('{name} {description} {email} {domain_id}'.format(**u))
  elif argv[0] == 'get':
    for user_name in argv[1:]:
      users = cc.iam.users(user_name)
      if len(users) != 1:
        print('{user_name} not matched')
        continue
      u = users[0]
      print(json.dumps(u,indent=2))
  elif argv[0] == 'add' or argv[0] == 'create' or argv[0] == 'new':
    domain_id = None
    for p in cc.iam.projects():
      domain_id = p['domain_id']
      break
    if domain_id is None:
      print('Unable to find a suitable domain ID')
      exit(1)

    # name
    # password
    # email
    # pwd_status : False
    # description

      print(json.dumps(p,indent=2))
      # ~ details = cc.iam.get_project_details(p['id'])
    # ~ add
    # ~ name
    #

    # ~ if len(argv) >= 2:
      # ~ user_name = argv[1]
      # ~ desc = None if len(argv) == 2 else argv[2]

      # ~ newid = cc.iam.new_group(grpname, desc)
      # ~ print('grp id', newid)
  # ~ elif argv[0] == 'del' or argv[0] == 'rm' or argv[0] == 'remove':
    # ~ try:
      # ~ grps = cc.iam.groups(argv[1])
      # ~ cc.iam.del_group(grps[0]['id'])
    # ~ except KeyError:
      # ~ print('Group already deleted')
  else:
    print('Usage')
    print('default : list users')
    print('get group : get details for group')
    print('add grpname [descp: add new group')
    print('del grpname : del group')


