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

admin_group = f'{project_name}-admin'

if len(argv) == 1 and argv[0] == 'create':
  q = cc.iam.projects(region_name)
  region = q[0]['id']

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
  
  ...
else:
  print("Usage")
  print(f" create : create project {region_name}_{project_name}")
  print(" create : delete project -- make sure all resources are released first")

# Create API user
# Delete API user
