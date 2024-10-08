#
# Project recipe
#
'''
## Project recipes

## list projects

Get a list of projects

```bash
scullery prj
```

## get project details

Get details of a project

```bash
scullery prj get region_projectname
```

## add project

Create a new project

```bash
scullery prj add region_projectname [description]
```

## del project region_projectname

Delete an existing project

```bash
scullery prj del region_projectname [--force]
```

**NOTE** Project deleletion takes more than 30 minutes.

This recipe will check using Resource Management that no
active resources are assigned to this project.  Use `--force`
to ignore.

## grant permissions on project

Grants a role to a group on a project

```bash
scullery prj grant rolename on region_projectname to groupname
```

## revoke permissions on project

Revokes a role from a group on a project

```bash
scullery prj revoke rolename on region_projectname from groupname
```
***
'''
import json
import os
import sys

from scullery import cloud

def run(argv:list[str]) -> None:
  '''Manage projects (verbs: <none>, get, add, del, grant, revoke)'''
  cc = cloud()

  if len(argv) == 0:
    for p in cc.iam.projects():
      details = cc.iam.get_project_details(p['id'])
      print('{id} {name:22} {status:8} {description}'.format(**details))
      # ~ print(json.dumps(details, indent=2))
  elif argv[0] == 'get':
    grps = cc.iam.groups()
    prjlst = cc.iam.projects(name=argv[1])
    for prj in prjlst:
      details = cc.iam.get_project_details(prj['id'])
      print('id:        {id}\n  name:    {name}\n  desc:    {description}\n  enabled: {enabled}\n  status:  {status}'.format(**details))
      roles = {}
      for g in grps:
        gr = cc.iam.get_project_group_perms(prj['id'], g['id'])
        if len(gr) > 0:
          roles[g['id']] = [ g['name'] ]
          q = ''
          rstr = ''
          for r in gr:
            rstr += q + r['display_name']
            q = ', '
          roles[g['id']].append(rstr)
      if len(roles) > 0:
        print('  roles per group')
        for role in roles.values():
          print('    {0}: {1}'.format(*role))
  elif argv[0] == 'add' or argv[0] == 'create' or argv[0] == 'new':
    print(len(argv))
    if len(argv) >= 2:
      prjname = argv[1]
      desc = f'Project created by {os.getlogin()} using scullery' if len(argv) == 2 else argv[2]
      if not '_' in prjname:
        print('No region specified')
        return
      region, _ = prjname.split('_',1)
      regdat = cc.iam.projects(name=region)
      if len(regdat) != 1:
        print(f'Unknown region {region}')
        return

      newid = cc.iam.new_project(prjname, regdat[0]['id'], desc)
      print('prj id', newid)
    else:
      print('Usage: add <prjname> [description]')
  elif argv[0] == 'del' or argv[0] == 'rm' or argv[0] == 'remove':
    try:
      prjdat = cc.iam.projects(argv[1])
      if len(prjdat) != 1:
        print('Unable to find project')
        return
      res = cc.rms.resources(argv[1])
      if len(res) > 0:
        print(f'Warning: Project {argv[1]} has {len(res)} active resources')
        if not '--force' in argv:
          print('Use --force option to continue regardless')
          print('')
          print('Resources found:')
          for rs in res:
            print('  {provider}.{type} {name}'.format(**rs))

          return
      cc.iam.del_project(prjdat[0]['id'])
    except KeyError:
      print('Project already deleted')
  elif argv[0] == 'grant':
    role = argv[1]
    group = None
    project = None
    argv = argv[2:]
    while len(argv) > 0 and (argv[0] == 'on' or argv[0] == 'to'):
      if argv[0] == 'on':
        project = argv[1]
        argv = argv[2:]
      elif argv[0] == 'to':
        group = argv[1]
        argv = argv[2:]

    if role is None:
      role = argv[0]
      argv = argv[1:]
    if group is None:
      group = argv[0]
      argv = argv[1:]

    q = cc.iam.projects(name=project)
    if len(q) != 1:
      sys.stderr.write(f'Error matching project {project}\n')
      exit(8)
    prj_id = q[0]['id']
    q = cc.iam.groups(name=group)
    if len(q) != 1:
      sys.stderr.write(f'Error matching group {group}\n')
      exit(3)
    grp_id = q[0]['id']
    q = cc.iam.get_role(role)
    role_id = q['id']

    print('role',role, role_id)
    print('group',group, grp_id)
    print('project',project, prj_id)

    cc.iam.grant_project_group_perms(prj_id, grp_id, role_id)

  elif argv[0] == 'revoke':
    role = argv[1]
    group = None
    project = None
    argv = argv[2:]
    while len(argv) > 0 and (argv[0] == 'on' or argv[0] == 'from'):
      if argv[0] == 'on':
        project = argv[1]
        argv = argv[2:]
      elif argv[0] == 'from':
        group = argv[1]
        argv = argv[2:]

    if role is None:
      role = argv[0]
      argv = argv[1:]
    if group is None:
      group = argv[0]
      argv = argv[1:]

    q = cc.iam.projects(name=project)
    if len(q) != 1:
      sys.stderr.write(f'Error matching project {project}\n')
      exit(8)
    prj_id = q[0]['id']
    q = cc.iam.groups(name=group)
    if len(q) != 1:
      sys.stderr.write(f'Error matching group {group}\n')
      exit(3)
    grp_id = q[0]['id']
    q = cc.iam.get_role(role)
    role_id = q['id']

    print('role',role, role_id)
    print('group',group, grp_id)
    print('project',project, prj_id)

    cc.iam.revoke_project_group_perms(prj_id, grp_id, role_id)

  else:
    print('Usage')
    print('default : list projects')
    print('get project prjname : get details for project')
    print('add prjname description : add project')
    print('del prjname: del kermit project -- make sure all resources are deleted before using this')
    print('grant role on project to group : assign permissions')
    print('')
    print('Note that for kermit created projects, it is recomended to')
    print('delete them using the kermit delete recipe instead of "prj del"')
    



