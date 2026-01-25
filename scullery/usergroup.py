'''
User functions

'''
import os
from typing import Any

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from scullery import api

def add_user(cc:api.ApiSession,
              name:str|None = None,
              passwd:str|None = None,
              description:str|None = None,
              email:str|None = None,
              project:str|None = None,
              groups:list[str]|None = None) -> dict[str,str]:
  result = dict()

  domain_id = cc.iam.domain()
  new_user = {
    'pwd_status': False,
    'domain_id': domain_id,
    'description': f'-- user created by {os.getlogin()} using scullery',
  }

  if name is None:
    new_user['name'] = cc.iam.gen_user_name()
    result['name'] = new_user['name']
  else:
    new_user['name'] = name
    result['name'] = name

  if passwd is None:
    new_user['password'] = cc.iam.gen_user_password()
    result['password'] = new_user['password']
  else:
    new_user['password'] = passwd

  if email is not None: new_user['email'] = email
  if project is not None:
    new_user['description'] += f' -- project:{project}'
  if description is not None:
    new_user['description'] += f'\n{description}'

  gids = dict()
  if groups:
    # Make sure groups exist!
    for g in groups:
      q = cc.iam.groups(g)
      if len(q) != 1: raise KeyError(g)
      gids[q[0]['name']] = q[0]['id']

  # ~ print(new_user, groups)
  newid = cc.iam.new_user(**new_user)
  result['id'] = newid
  for gname,gid in gids.items():
    cc.iam.add_group_user(gid, newid)
  return result


def add_group(cc:api.ApiSession,
              name:str,
              description:str|None = None,
              project:str|None = None):
  desc = f'-- group created by {os.getlogin()} using scullery'
  if project is not None: desc += f' -- project:{project}'
  if description is not None: desc += f'|{description}'
  return cc.iam.new_group(name, desc)

def add_role(cc:api.ApiSession,
              name:str,
              policy:Any,
              description:str|None = None,
              project:str|None = None):
  desc = f'-- role created by {os.getlogin()} using scullery'
  if project is not None: desc += f' -- project:{project}'
  if description is not None: desc += f'|{description}'
  return cc.iam.new_role(display_name = name, policy = policy,
                          description = desc)

if __name__ == '__main__':
  import api
  import creds
  cfg = creds.creds(cloud_name = 'otc-de-iam')
  api = api.ApiSession(cfg)


  del(api)

