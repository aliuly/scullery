#
# Roles recipe
#
'''
## Role recipes

Implements role recipes.

## list roles

List custom roles

```bash
scullery role
```
## list SYSTEM roles

List system roles.  These roles are built-in into the cloud infrastructure.

```bash
scullery role system
```

## get role details

Get the role details.

```bash
scullery role get role_name
```
## add custom role

Create a new custom role

```bash
scullery role add role_name [yaml_file]
```
Create a role using a `yaml_file`.  If no `yaml_file` is specified
it will read definition from `stdin`.

Example YAML:

```yaml
- Action:
  - 'ecs:*:get*'
  - 'ecs:*:list*'
  - 'ecs:*:stop*'
  - 'ecs:*:start*'
  - 'ecs:*:reboot*'
  Effect: Allow
```

See {py:obj}`scullery.iam.Iam.new_role` for more details.

## delete custom role

Delete a custom role

```bash
scullery role del role_name
```
***
'''

import json
import os
import sys
import yaml

from scullery import cloud

# ~ kermit_role = 'ACME-kermit-operator'
    # ~ [
          # ~ { 'Action': ['ecs:*:get*',
                        # ~ 'ecs:*:list*',
                        # ~ 'ecs:*:stop*',
                        # ~ 'ecs:*:start*',
                        # ~ 'ecs:*:reboot*'],
             # ~ 'Effect': 'Allow'}])

def dump_roles(roles:list) -> None:
  '''INTERNAL: print role details

  :param roles: List of roles to primt
  '''
  for role in roles:
    values = {
      'description': '',
      'display_name': '',
    }
    values.update(role)
    print('{name:16} {type} {display_name:24} {description}'.format(**values))

def run(argv:list[str]) -> None:
  '''Manage roles (verbs: <none>, system, get, add, del)'''
  cc = cloud()

  if len(argv) == 0:
    dump_roles(cc.iam.custom_roles())
    # ~ resp = cc.get(f'https://iam.{cc.region}.otc.t-systems.com/v3/roles', params = {
      # ~ 'name': 'te_admin',
    # ~ })
    # ~ print(json.dumps(resp.json(),indent=2))
  elif argv[0] == 'system':
    dump_roles(cc.iam.system_roles())
  elif argv[0] == 'get':
    for role_name in argv[1:]:
      role = cc.iam.get_role(role_name)
      print(json.dumps(role, indent=2))
  elif argv[0] == 'add' or argv[0] == 'create' or argv[0] == 'new':
    if len(argv) == 2:
      # Read from stdin
      print('Enter policy rules')
      policies = yaml.safe_load(sys.stdin)
    elif len(argv) == 3:
      with open(argv[2],'r') as fp:
        policies = yaml.safe_load(fp)
    else:
      print('Usage: scullery roles add <role-name> [yaml-data]')
      exit(1)
    new_role = cc.iam.new_role(display_name = argv[1], policy = policies,
              description = f'Role created by {os.getlogin()} using scullery' )
    print(json.dumps(new_role, indent=2))
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


