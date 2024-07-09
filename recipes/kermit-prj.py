#
# New project recipe
#
import json
import sys
from scullery import cloud

cc = cloud()

region_name = 'eu-de'
project_name = "testprj"
project_desc = 'test project'
groups = [
  [ 'admin', 'te_admin' ],
  [ 'kermit', 'ACME-kermit-jump' ],
]
# TODO create one admin user
# TODO save to a Tofu credentials file
# TODO move it to a built-in recipe that accepts a config file
# TODO when deleting
# TODO save users in groups
# TODO after groups are deleted, delete users that are not in any groups


admin_group = f'{project_name}-admin'

if len(argv) == 1 and argv[0] == 'create':
  q = cc.iam.projects(region_name)
  region = q[0]['id']
  domain = q[0]['domain_id']

  roles_dict = dict()
  project = cc.iam.new_project(f'{region_name}_{project_name}', region, project_desc)
  print('Created project',project)
  for gp in groups:
    grp_basename, grp_role = gp
    if not grp_role in roles_dict:
      roles_dict[grp_role] = cc.iam.get_role(grp_role)
    # ~ print(json.dumps(roles_dict[grp_role],indent=2))
    role = roles_dict[grp_role]['id']
    # ~ print(role)

    # Create a project group...
    group = cc.iam.new_group(f'{project_name}-{grp_basename}', f'{grp_basename} users for {region_name}_{project_name}')
    print('Created group',group)
    cc.iam.grant_project_group_perms(project, group, role)
    print('Authorized',project,group, role)

elif len(argv) == 1 and argv[0] == 'delete':
  q = cc.iam.projects(f'{region_name}_{project_name}')
  if len(q) != 1:
    sys.stderr.write('Project not found\n')
    exit(5)
  project = q[0]['id']

  roles_dict = dict()
  for gp in groups:
    grp_basename, grp_role = gp
    if not grp_role in roles_dict:
      roles_dict[grp_role] = cc.iam.get_role(grp_role)
    role = roles_dict[grp_role]['id']

    q = cc.iam.groups(f'{project_name}-{grp_basename}')
    if len(q) != 1:
      sys.stderr.write(f'Missing group {project_name}-{grp_basename}\n')
      continue
    group = q[0]['id']

    print('Revoking',project,group, role)
    cc.iam.revoke_project_group_perms(project, group, role)

    print('Delete',group)
    cc.iam.del_group(group)

  print('Delprj',project)
  cc.iam.del_project(project)
else:
  print("Usage")
  print(f" create : create project {region_name}_{project_name}")
  print(" create : delete project -- make sure all resources are released first")

# Create API user
# Delete API user
