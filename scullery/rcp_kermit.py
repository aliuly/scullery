#
# Kermit recipes
#
'''
## Kermit recipe implementations

Used to set-up and dismantle project environments.

## set-up

Setting up a project will:

1. create project to scope the work
2. create groups and assign them project related roles.  By default
   it will create the following groups:
   - admin : Full resource admin access
   - guest : Read-only access
3. create users for the created groups.  By default it will create
   random users with random passwords.

Additional users/credentials can be created using the `user` recipe and
assigned to the created groups.

If setting up a project using defaults you only need to use:

```bash
scullery kermit setup --defaults=region_project-name --output=info.yaml
```

If you want to tweak the project configuration you need to use a YAML
file:

```bash
scullery kermit setup --spec=input.yaml --output=info.yaml
```

Example YAML file:

```yaml
# project is the only mandatory configuration item
project: eu-de_testprj

# Everything from here on is optional
description: testprj description

# If domain_id is not specified it will use one from the region
# or the default for the logged-in user
domain_id: '*change_me*'
# If parent_id is not specified it will use the one from the region
parent_id: '*change_me*'

#
# If groups section does not exist, a default set of groups will be
# created
#
# Groups section contains a base group name, and the role that it
# will be assigned
#
groups:
  admin: te_admin
  guest: readonly
  ops: ACME-kermit-jump

#
# If the users section does not exists a users section will be
# generated with one random user for each group defined earlier
#
# Users should contain a "User_name" and a "group_name" that the
# user will be assigned to.
users:
  my_admin: admin
  my_guest: guest

#
# The creds section is used to define initial password for newly
# created users.
#
# It should contain mappings of "user: password"
#
# if a user defined in users does not have a matching password in
# the creds section a random password will be assigned.
#
creds:
  my_admin: change_Me123
```

## delete

To delete a project:

```bash
scullery kermit del region_project-name [--force] [--execute]
```
This will delete all the set-up done by the `setup` option.

This recipe will use the Resource Management service to check
if there are no active resources associated with the project.
If there are it will stop unless the `--force` option is used.

By default, it will simply show on the screen the actions that
will be implemented.  Use the `--execute` command to actually
perform changes to the cloud.

***
'''

import argparse
import os
import sys
import yaml

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from scullery import cloud
from scullery import parsers
from scullery import usergroup

def kermit(args:argparse.Namespace):
  if args.desc is None:
    args.desc = f'-- kermit-project created by {os.getlogin()} using scullery'
  else:
    args.desc = f'-- kermit-project created by {os.getlogin()} using scullery|{args.desc}'
  if args.spec is None:
    root,_ = os.path.splitext(__file__)
    args.spec = open(root+'.yaml','r')

  ytxt = args.spec.read().format(project = args.project,
                                  description = args.desc)
  spec = yaml.safe_load(ytxt)

  if '_' not in args.project:
    raise ValueError(f'Project name {args.project} does not have a region')

  cc = cloud()
  region, _ = args.project.split('_',1)
  q = cc.iam.projects(name = region)
  if len(q) != 1: raise KeyError(region)
  regdat = q[0]

  ############################# TESTING ##########################
  prj_id = cc.iam.new_project(args.project, regdat['id'], args.desc)
  sys.stderr.write(f'New project id: {prj_id}\n')
  # ~ q = cc.iam.projects(name = args.project)
  # ~ prj_id = q[0]['id']
  # ~ sys.stderr.write(f'Existing project id: {prj_id}\n')

  role_rec = dict()
  if 'roles' in spec:
    for role,perms in spec['roles'].items():
      role_rec[role] = usergroup.add_role(cc, role,
                              policy = perms, project = args.project)
      sys.stderr.write(f'New role {role}: {role_rec[role]["id"]}\n')

  group_ids = dict()
  if 'groups' in spec:
    for group, role in spec['groups'].items():
      group_ids[group] = usergroup.add_group(cc, group,
                                            project = args.project)
      sys.stderr.write(f'New group {group}: {group_ids[group]}\n')
      if role in role_rec:
        role_id = role_rec[role]['id']
      else:
        q = cc.iam.get_role(role)
        role_id = q['id']

      cc.iam.grant_project_group_perms(prj_id, group_ids[group], role_id)
      sys.stderr.write(f'Granted {role} on project to {group}\n')

  creds = spec['creds'] if 'creds' in spec else dict()
  user_rec = dict()

  output_data = list()

  if 'users' in spec:
    for user, group in spec['users'].items():
      if user not in creds:
        creds[user] = cc.iam.gen_user_password()
      user_rec[user] = usergroup.add_user(cc,
                              name = user,
                              passwd = creds[user],
                              project = args.project,
                              groups = [ group ])
      sys.stderr.write(f'New user {user}: {user_rec[user]["id"]}\n')

      output_data.append({
        'ii': len(output_data),
        'user': user,
        'passwd': creds[user],
        'project': args.project,
        'domain': cc.domain_name,
      })

  if args.output.name.endswith('.yaml'):
    args.output.write('clouds:\n')
    template = (
                '  otc-{ii}:\n'
                '    profile: otc\n'
                '    auth:\n'
                '      project_name: {project}\n'
                '      user_domain_name: {domain}\n'
                '      username: {user}\n'
                '      password: {passwd}\n'
               )
  else:
    args.output.write('#, user_domain_name, project_name, username, password\n')
    template = '{ii}, {domain}, {project}, {user}, {passwd}\n'

  for dat in output_data:
    args.output.write(template.format(**dat))


def parser(subp):
  pr = subp.add_parser('kermit',
                        help = 'Kermit recipe',
                        aliases = ['ker','kk'])
  pr.set_defaults(recipe_cb = kermit)
  pr.add_argument('project',
                  help = 'Project name')
  pr.add_argument('-d','--description','--desc', dest = 'desc',
                  help = 'Project description')
  pr.add_argument('-s','--spec',
                  type = argparse.FileType('r'), default = None,
                  help = 'Spec file')
  pr.add_argument('-o','--output',
                  type = argparse.FileType('x'), default = sys.stdout,
                  help = 'Output file')

parsers.register_parser('kermit',parser)








