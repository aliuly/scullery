'''

This module implements user related recipes.  The following
verbs are recognized.

| recipe | descripiton |
|---|----|
|  | List cloud users |
| get username | Get user details for a given user |
| add [options] | Create user |
| del username | Delete user |
| group groupname add username | Add user to group |
| group groupname del username | Remove user from group |

'''
#
# Users recipe
#
import argparse
import json

import sys
import yaml

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from . import parsers
from . import formatters
from . import usergroup
from . import clouds



# Columns for the list (default table) view.
COLUMNS: formatters.Columns = [
  ('name',        'Name'),
  ('description', 'Description'),
  ('email',       'Email'),
]

def mod_group(args: argparse.Namespace) -> None:
  '''Add or remove a user from a group'''
  cc = clouds.session(args)
  q = cc.iam.groups(args.group)
  if len(q) != 1:
    sys.stderr.write(f'Unmatched group {args.group}\n')
    exit(4)
  group = q[0]
  q = cc.iam.users(args.user)
  if len(q) != 1:
    sys.stderr.write(f'Unmatched user {args.user}\n')
    exit(4)
  user = q[0]
  if args.op == 'add':
    cc.iam.add_group_user(group['id'],user['id'])
  elif args.op == 'del':
    cc.iam.del_group_user(group['id'],user['id'])
  else:
    raise KeyError(args.op)

def list_users(args: argparse.Namespace) -> None:
  '''List all users'''
  cc = clouds.session(args)
  data = cc.iam.users()
  # Ensure description key exists for every user (current code did this)
  for u in data:
    u.setdefault('description', '')
  rows = formatters.extract_rows(data, COLUMNS)
  formatters.write_output(rows, COLUMNS, args.format)

def get_user(args: argparse.Namespace) -> None:
  '''Show detailed info for one or more users'''
  cc = clouds.session(args)
  for user_name in args.user:
    users = cc.iam.users(user_name)
    if len(users) != 1:
      print(f'{user_name} not matched')
      continue
    u = users[0]

    if args.format == 'terminal':
      print(json.dumps(u, indent=2))
      q = cc.iam.user_groups(u['id'])
      if len(q) > 0:
        print('groups:')
        for g in q:
          print('  {name} {description}'.format(**g))
    else:
      out = dict(u)
      out['groups'] = cc.iam.user_groups(u['id'])
      formatters.write_single_output(out, args.format)

def add_user(args: argparse.Namespace) -> None:
  '''Create a new user'''
  cc = clouds.session(args)

  res = usergroup.add_user(cc,
              name = args.name,
              passwd = args.passwd,
              description = args.description,
              email = args.email,
              project = args.project,
              groups = args.group)
  print(yaml.dump(res))

def del_user(args: argparse.Namespace) -> None:
  '''Delete one or more users'''
  cc = clouds.session(args)
  for u in args.name:
    try:
      user = cc.iam.users(u)
      if len(user) != 1: raise KeyError(u)
      cc.iam.del_user(user[0]['id'])
      sys.stderr.write(f'Removed user: {u} ({user[0]["id"]})\n')
    except KeyError:
      sys.stderr.write(f'{u}: User not found\n')

def set_passwd(args: argparse.Namespace) -> None:
  '''Set or reset a user password'''
  cc = clouds.session(args)

  q = cc.iam.users(args.user)
  if len(q) != 1: raise KeyError(args.user)
  user_id = q[0]['id']
  if args.password is None:
    args.password = cc.iam.gen_user_password()
    print('password', args.password)
  cc.iam.reset_passwd( user_id, args.password, args.set_pwd)

def sphinxarg() -> argparse.ArgumentParser:
  return parsers.sphinxarg_common(
        sys.modules[__name__].__doc__,
        parser,
  )


def parser(subp: argparse.ArgumentParser) -> None:
  '''Register the ``users`` sub-parser'''
  pr = subp.add_parser('user',
                        help = 'User recipes',
                        aliases = ['usr'])
  pr.set_defaults(recipe_cb = list_users)
  formatters.add_format_arg(pr)
  usp = pr.add_subparsers(title='op',
                          description='Operation.  If not spcified, list users.',
                          required = False,
                          help = 'Operation')
  pp = usp.add_parser('get',
      help = 'Get details for user',
  )
  pp.add_argument('user',
                  help='User to look-up',
                  nargs='+')
  pp.set_defaults(recipe_cb = get_user)
  formatters.add_single_format_arg(pp)

  pp = usp.add_parser('add',
                  help = 'Add user',
                  aliases = ['new','create'])

  pp.add_argument('-P','--password','--passwd', dest = 'passwd',
                  help = 'Password to use (if not specified a random password is used)')
  pp.add_argument('-n','--name', '--user', dest = 'name',
                  help = 'User name to create (it not specified a random name is used)')
  pp.add_argument('-m','-e','--email','--mail', dest = 'email',
                  help = 'Assign e-mail address')
  pp.add_argument('-d','--description','--desc', dest = 'description',
                  help = 'Description for this user')
  pp.add_argument('-p','--project','--proj', dest = 'project',
                  help = 'Include project name in description')
  pp.add_argument('-g','--group','--grp', dest = 'group',
                  action = 'append', default = [],
                  help = 'Assign group (can be specified multiple times)')

  pp.set_defaults(recipe_cb = add_user)

  pp = usp.add_parser('del',
                  help = 'Delete user',
                  aliases = ['rm'])
  pp.add_argument('name',
                  nargs='+',
                  help='User name to delete')
  pp.set_defaults(recipe_cb = del_user)

  pp = usp.add_parser('group',
                  help = 'Modify user group membership',
                  aliases = ['grp'])
  pp.add_argument('group',
                  help='Group to modify')
  pp.add_argument('op',
                  choices=['add','del'],
                  help='Add or Delete operation')
  pp.add_argument('user',
                  help='User to add/del from group')
  pp.set_defaults(recipe_cb = mod_group)

  pp = usp.add_parser('passwd',
                      help = 'set/reset user password',
                      aliases = [ 'reset-passwd', 'password', 'set-passwd'])
  pp.add_argument('-S', '--chg-pwd', dest = 'set_pwd',
                      help = 'Ask password to be changed on first login',
                      action = 'store_true', default = False)
  pp.add_argument('user',
                  help = 'User to modify')
  pp.add_argument('password',
                  nargs='?',
                  help='Password to set (if not specify will use a random string)')
  pp.set_defaults(recipe_cb = set_passwd)

parsers.register_parser('users',parser)
