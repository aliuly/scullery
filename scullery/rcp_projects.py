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
import argparse
import json
import os
import re
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from scullery import cloud
from scullery import parsers

RE_PRJSIG = re.compile(r'^-- \S+ created by \S+ using scullery -- project:(\S+)($|\|)')

def add_prj(args:argparse.Namespace):
  cc = cloud()

  desc = f'-- Project created by {os.getlogin()} using scullery'
  if args.description is not None:
    desc += f'|{args.description}'

  if '_' not in args.name:
    raise ValueError(f'Project name {args.name} does not have a region')

  region, _ = args.name.split('_',1)
  regdat = cc.iam.projects(name = region)

  if len(regdat) != 1: raise KeyError(region)

  newid = cc.iam.new_project(args.name, regdat[0]['id'], desc)
  sys.stderr.write(f'Project ID={newid}\n')

def list_prj(args:argparse.Namespace):
  cc = cloud()
  for p in cc.iam.projects():
    details = cc.iam.get_project_details(p['id'])
    print('{id} {name:22} {status:8} {description}'.format(**details))
      # ~ print(json.dumps(details, indent=2))

def get_prj(args:argparse.Namespace):
  cc = cloud()
  grps = cc.iam.groups()
  for prj_name in args.project:
    prjlst = cc.iam.projects(name=args.project)
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


def del_prj(args:argparse.Namespace):
  cc = cloud()
  for prjname in args.name:
    try:
      prjdat = cc.iam.projects(prjname)
      if len(prjdat) != 1: raise KeyError(prjname)

      res = cc.rms.resources(prjname)
      if len(res) > 0:
        sys.stderr.write(f'Warning: Project {prjname} has {len(res)} active resources\n')
        if not args.force:
          sys.stderr.write('Use --force option to continue regardless\n\n')
          sys.stderr.write('Resources found:\n')
          for rs in res:
            sys.stderr.write('- {provider}.{type} {name}\n'.format(**rs))
          continue

      # Delete any associated users...
      for u in cc.iam.users():
        if 'description' not in u: continue
        if not (mv := RE_PRJSIG.search(u['description'])): continue
        if mv.group(1) != prjname: continue
        cc.iam.del_user(u['id'])
        sys.stderr.write(f'Deleted user {u["name"]}\n')

      # Delete any associated groups
      for g in cc.iam.groups():
        if 'description' not in g: continue
        if not (mv := RE_PRJSIG.search(g['description'])): continue
        if mv.group(1) != prjname: continue
        cc.iam.del_group(g['id'])
        sys.stderr.write(f'Deleted group {g["name"]}\n')

      # Delete any associated roles
      for r in cc.iam.custom_roles():
        if 'description' not in r: continue
        if not (mv := RE_PRJSIG.search(r['description'])): continue
        if mv.group(1) != prjname: continue
        cc.iam.del_role(r['id'])
        sys.stderr.write(f'Deleted role {r["name"]}\n')

      ############################# TESTING ##########################
      # ~ sys.stderr.write(f'NOT Deleted {prjname} ({prjdat[0]["id"]})\n')
      cc.iam.del_project(prjdat[0]['id'])
      sys.stderr.write(f'Deleted {prjname} ({prjdat[0]["id"]})\n')
    except KeyError:
      sys.stderr.write(f'{prjname}: Project not found\n')

def grant_prj(args:argparse.Namespace):
  cc = cloud()

  role = args.grants[0]
  group = None
  project = None
  argv = args.grants[1:]
  while len(argv) > 0:
    if argv[0] == 'on':
      project = argv[1]
      argv = argv[2:]
    elif argv[0] == 'to':
      group = argv[1]
      argv = argv[2:]
    else:
      if project is None:
        project = argv[0]
        argv = argv[1:]
      elif group is None:
        group = argv[0]
        argv = argv[1:]
      else:
        raise SyntaxError(f'Error grants: {' '.join(args.grants)}')

  if project is None or group is None:
    raise SyntaxError(f'Grant requires project and group to be specified')

  q = cc.iam.projects(name=project)
  if len(q) != 1: raise KeyError(project)
  prj_id = q[0]['id']

  q = cc.iam.groups(name=group)
  if len(q) != 1: raise KeyError(group)
  grp_id = q[0]['id']

  q = cc.iam.get_role(role)
  role_id = q['id']

  print('role',role, role_id)
  print('group',group, grp_id)
  print('project',project, prj_id)

  cc.iam.grant_project_group_perms(prj_id, grp_id, role_id)

def revoke_prj(args:argparse.Namespace):
  cc = cloud()

  role = args.revokes[0]
  group = None
  project = None
  argv = args.revokes[1:]
  while len(argv) > 0:
    if argv[0] == 'on':
      project = argv[1]
      argv = argv[2:]
    elif argv[0] == 'from':
      group = argv[1]
      argv = argv[2:]
    else:
      if project is None:
        project = argv[0]
        argv = argv[1:]
      elif group is None:
        group = argv[0]
        argv = argv[1:]
      else:
        raise SyntaxError(f'Error revoking: {' '.join(args.revokes)}')

  if project is None or group is None:
    raise SyntaxError(f'Revoking requires project and group to be specified')

  q = cc.iam.projects(name=project)
  if len(q) != 1: raise KeyError(project)
  prj_id = q[0]['id']

  q = cc.iam.groups(name=group)
  if len(q) != 1: raise KeyError(group)
  grp_id = q[0]['id']

  q = cc.iam.get_role(role)
  role_id = q['id']

  print('role',role, role_id)
  print('group',group, grp_id)
  print('project',project, prj_id)
  cc.iam.revoke_project_group_perms(prj_id, grp_id, role_id)


def parser(subp):
  pr = subp.add_parser('project',
                        help = 'Project Management service',
                        aliases = ['projects', 'prj','p'])
  pr.set_defaults(recipe_cb = list_prj)

  sp = pr.add_subparsers(title='op',
                          description='Operation.  If not spcified, list projects.',
                          required = False,
                          help = 'Operation')

  pp = sp.add_parser('get',
                  help = 'Get details for project',
                  aliases = ['g'])
  pp.add_argument('project',
                  help='Project to look-up',
                  nargs='+')
  pp.set_defaults(recipe_cb = get_prj)

  pp = sp.add_parser('add',
                  help = 'Add Project',
                  aliases = ['create', 'new','a'])
  pp.add_argument('-d','--description', '--desc', dest='description',
                    help = 'Optional description')
  pp.add_argument('name',
                  help='Project name')
  pp.set_defaults(recipe_cb = add_prj)

  pp = sp.add_parser('del',
                  help = 'Delete Project',
                  aliases = ['remove', 'rm','r'])
  pp.add_argument('-f','--force',
                    action='store_true', default=False,
                    help = 'Force remove even if resources exists')
  pp.add_argument('name',
                  nargs = '+',
                  help='Project name to delete')
  pp.set_defaults(recipe_cb = del_prj)

  pp = sp.add_parser('grant',
                  help = 'Grant roles',
                  aliases = ['gr'])
  pp.add_argument('grants',
      nargs='+',
      help='Enter "role" [on] "project" [to] "group"')

  pp.set_defaults(recipe_cb = grant_prj)

  pp = sp.add_parser('revoke',
                  help = 'Revoke roles',
                  aliases = ['rev'])
  pp.add_argument('revokes',
      nargs='+',
      help='Enter "role" [on] "project" [from] "group"')

  pp.set_defaults(recipe_cb = revoke_prj)

parsers.register_parser('projects',parser)

