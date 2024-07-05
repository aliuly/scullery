#
# Roles recipe
#
import json

from scullery import cloud

kermit_role = 'ACME-kermit-operator'

def dump_roles(roles):
  for role in roles:
    values = {
      'description': '',
      'display_name': '',
    }
    values.update(role)
    print('{name:16} {type} {display_name:24} {description}'.format(**values))

def run(argv:list[str]) -> None:
  print(argv)
  cc = cloud()

  if len(argv) == 0:
    dump_roles(cc.iam.custom_roles())
  elif argv[0] == 'system':
    dump_roles(cc.iam.system_roles())
  elif argv[0] == 'get':
    for role_name in argv[1:]:
      role = cc.iam.get_role(role_name)
      print(json.dumps(role, indent=2))
  elif argv[0] == 'add' or argv[0] == 'create' or argv[0] == 'new':
    new_role = cc.iam.new_role(display_name = kermit_role, policy = [
          { 'Action': ['ecs:*:get*',
                        'ecs:*:list*',
                        'ecs:*:stop*',
                        'ecs:*:start*',
                        'ecs:*:reboot*'],
             'Effect': 'Allow'}])
    print(json.dumps(new_role, indent=2))
  elif argv[0] == 'del' or argv[0] == 'rm' or argv[0] == 'remove':
    try:
      role = cc.iam.get_role(kermit_role)
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
    

