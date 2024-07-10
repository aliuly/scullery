#
# Kermit recipes
#
'''Kermit recipe implementations'''

import os
import sys
import yaml

from scullery import cloud

def usage():
  '''Show recipe usage'''
  print('Usage')
  print('  create --spec=file --output=file')
  print('  del prj')

def group_in_other_projects(cc, grp:dict, prjid:str, all_projects:list) -> bool:
  '''INTERNAL: Check if project is used elsewhere

  :param cc: Cloud connection
  :param grp: group details
  :param prjid: project id
  :param all_projects: list of all projects
  :returns: True if the group is referenced elsewhere.  False if the project is only used by prjid.\

  It will check if the given group is referenced by the other projects we have
  access to.  This is used to decide if we need to delete a group once
  the project is deleted.
  '''
  for p in all_projects:
    if prjid == p['id']: continue

    xroles = cc.iam.get_project_group_perms(p['id'], grp['id'])
    if len(xroles) > 0: return True

  xroles = cc.iam.get_domain_group_perms(grp['domain_id'], grp['id'])
  if len(xroles) > 0: return True
  return False

def run(argv:list[str]) -> None:
  '''Kermit recipes (verb: create,del)'''
  cc = cloud()

  if len(argv) == 0:
    usage()
  elif argv[0] == 'create':
    spec_file = None
    out_file = None
    for opt in argv[1:]:
      if opt.startswith('--spec='):
        spec_file = opt[7:]
      elif opt.startswith('--output='):
        out_file = opt[9:]
      else:
        sys.stderr.write(f'Unknown option {opt}\n')
        exit(6)

    if spec_file is None:
      print('Enter specification')
      spec = yaml.safe_load(sys.stdin)
    else:
      with open(spec_file,'r') as fp:
        spec = yaml.safe_load(fp)

    if not 'groups' in spec or len(spec['groups']) == 0:
      spec['groups'] = {
        'admin': 'te_admin',
        'guest': 'readonly',
      }
    if not 'users' in spec or len(spec['users']) == 0:
      spec['users'] = dict()
      for g in spec['groups']:
        genuser = cc.iam.gen_user_name()
        spec['users'][genuser] = g
    if not 'creds' in spec: spec['creds'] = dict()
    for u in spec['users']:
      if not u in spec['creds']:
        spec['creds'][u] = cc.iam.gen_user_password()

    if not 'description' in spec:
      spec['description'] = f'Kermit project created by {os.getlogin()} using scullery'

    spec['region'], spec['project_base'] = spec['project'].split('_',1)
    if not 'domain_id' in spec:
      spec['domain_id'] = cc.iam.domain(spec['region'])

    if not 'parent_id' in spec:
      q = cc.iam.projects(spec['region'])
      spec['parent_id'] = q[0]['id']


    if out_file is None:
      print(yaml.dump(spec))
    else:
      with open(out_file,'w') as fp:
        fp.write(yaml.dump(spec))

    roles_dict = dict()
    groups_dict = dict()

    project = cc.iam.new_project(spec['project'], spec['parent_id'], spec['description'])
    print('Created project', project)
    for grp_basename, grp_role in spec['groups'].items():
      if not grp_role in roles_dict:
        roles_dict[grp_role] = cc.iam.get_role(grp_role)
      role = roles_dict[grp_role]['id']

      group = cc.iam.new_group(f'{spec["project_base"]}-{grp_basename}',
                              f'Kermit-Group {grp_role} created by {os.getlogin()} using scullery for {spec["project"]}')
      print('Created',grp_basename,'as',group)
      cc.iam.grant_project_group_perms(project, group, role)
      groups_dict[grp_basename] = group

    for username, usergroup in spec['users'].items():
      newuser = cc.iam.new_user(domain_id = spec['domain_id'],
                                name = username,
                                password = spec['creds'][username],
                                description = f'Kermit-User {usergroup} created by {os.getlogin()} using scullery for {spec["project"]}',
                                pwd_status = False)
      print('Created',username,'as',newuser)
      cc.iam.add_group_user(groups_dict[usergroup], newuser)
  elif argv[0] == 'del':
    prjdat = cc.iam.projects(argv[1])
    if len(prjdat) != 1:
      print('Unable to match project')
      return
    prjid = prjdat[0]['id']
    prjdat = cc.iam.get_project_details(prjid)
    if prjdat['status'] == 'deleting':
      print('{name} is already {status}'.format(**prjdat))
      return
    res = cc.rms.resources(argv[1])
    if len(res) > 0:
      print(f'Warning: Project {argv[1]} has {len(res)} active resources')
      if not '--force' in argv:
        print('Use --force option to continue regardless')
        return

    all_projects = cc.iam.projects()
    all_groups = cc.iam.groups()

    groups = dict()
    for g in all_groups:
      gr = cc.iam.get_project_group_perms(prjid, g['id'])
      if len(gr) > 0:
        # Make sure that this group is not being used elsewhere
        if group_in_other_projects(cc, g, prjid, all_projects):
          continue

        groups[g['name']] = g
        groups[g['name']]['roles'] = gr
    # ~ print(yaml.dump(groups))

    users = dict()
    seen_users = dict()
    for g in groups.values():
      for u in cc.iam.group_users(g['id']):
        if u['name'] in seen_users: continue
        seen_users[u['name']] = u

        xgrps = list()
        for xg in cc.iam.user_groups(u['id']):
          if xg['name'] in groups: continue
          xgrps.append(xg)
        if len(xgrps) != 0:
          sys.stderr.write(f'{u["name"]} member {g["name"]} will be skipped\n')
          continue

        users[u['name']] = u
        users[u['name']]['group'] = g['name']
    # ~ print(yaml.dump(users))

    # ... delete groups
    for g in groups.values():
      print('Delete group',g['name'],g['id'])
      cc.iam.del_group(g['id'])

    # ... delete users
    for u in users.values():
      print('Delete user',u['name'],u['id'])
      cc.iam.del_user(u['id'])

    # ... delete project
    print('Delete project',prjid)
    cc.iam.del_project(prjid)

  else:
    usage()









