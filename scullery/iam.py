#!python3
#
# API sessions
#
import random
import string

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

class Iam:
  API_HOST = 'iam.{region}.otc.t-systems.com'

  def api_path(self, path) -> str:
    host = Iam.API_HOST.format(region = self.session.region)
    return f'https://{host}/{path}'

  def __init__(self, session) -> None:
    self.session = session
    self.sys_roles = None
    self.usr_roles = None

  def system_roles(self) -> list:
    if self.sys_roles is None:
      resp = self.session.get(self.api_path('v3/roles'))
      if resp.status_code != 200 or not 'roles' in resp.json():
        raise RuntimeError(resp.text)
      self.sys_roles = resp.json()['roles']
    return self.sys_roles

  def custom_roles(self) -> list:
    if self.usr_roles is None:
      resp = self.session.get(self.api_path('v3.0/OS-ROLE/roles'))
      if resp.status_code != 200 or not 'roles' in resp.json():
        raise RuntimeError(resp.text)
      self.usr_roles = resp.json()['roles']
    return self.usr_roles

  def get_role(self, name:str) -> dict:
    self.custom_roles()
    for role in self.usr_roles:
      if role['name'] == name or ('display_name' in role and role['display_name'] == name): return role
    self.system_roles()
    for role in self.sys_roles:
      if role['name'] == name or ('display_name' in role and role['display_name'] == name): return role
    raise KeyError(f'Role "{name}" not found')

  def new_role(self, *, display_name:str, policy:dict|list, role_type:str = 'XA', description:str|None = None) -> dict:
    if description is None: description = f'Custom policy {display_name}'
    if isinstance(policy,list):
      policy = { 'Statement': policy, 'Version': '1.1' }
    else:
      if not 'Version' in policy: policy['Version'] = '1.1'
    resp = self.session.post(self.api_path('v3.0/OS-ROLE/roles'), json = {
      'role': {
        'display_name': display_name,
        'type': role_type,
        'description': description,
        'policy': policy,
      }
    })
    if resp.status_code != 201 or not 'role' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['role']

  def del_role(self, role_id:str) -> None:
    resp = self.session.delete(self.api_path(f'v3.0/OS-ROLE/roles/{role_id}'))
    if not resp.status_code in [200, 204]:
      raise RuntimeError(resp.text if resp.text else resp.reason)

  def users(self, name:str|None = None) -> list:
    params = dict() if name is None else { 'params': { 'name': name } }
    resp = self.session.get(self.api_path('v3/users'), **params)
    if resp.status_code != 200 or not 'users' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['users']

  def user_groups(self, usrid:str) -> list:
    resp = self.session.get(self.api_path(f'v3/users/{usrid}/groups'))
    if resp.status_code != 200 or not 'groups' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['groups']

  def new_user(self, **kwargs) -> list:
    resp = self.session.post(self.api_path('v3.0/OS-USER/users'), json = { 'user': kwargs })
    if resp.status_code != 201 or not 'user' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['user']['id']

  def del_user(self, usr_id:str) -> None:
    resp = self.session.delete(self.api_path(f'v3/users/{usr_id}'))
    if not resp.status_code in [200, 204]:
      raise RuntimeError(resp.text if resp.text else resp.reason)

  def groups(self, name:str|None = None) -> list:
    params = dict() if name is None else { 'params': { 'name': name } }
    resp = self.session.get(self.api_path('v3/groups'), **params)
    if resp.status_code != 200 or not 'groups' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['groups']

  def group_users(self, grpid:str) -> list:
    resp = self.session.get(self.api_path(f'v3/groups/{grpid}/users'))
    if resp.status_code != 200 or not 'users' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['users']

  def new_group(self, name:str, description:str|None = None) -> str:
    payload = { 'name': name }
    if not description is None: payload['description'] = description
    resp = self.session.post(self.api_path('v3/groups'), json=dict(group=payload))
    if resp.status_code != 201 or not 'group' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['group']['id']

  def del_group(self, grp_id:str) -> None:
    resp = self.session.delete(self.api_path(f'v3/groups/{grp_id}'))
    if not resp.status_code in [200, 204]:
      raise RuntimeError(resp.text if resp.text else resp.reason)

  def add_group_user(self, grp_id:str, usr_id:str) -> None:
    resp = self.session.put(self.api_path(f'v3/groups/{grp_id}/users/{usr_id}'))
    if resp.status_code != 204:
      raise RuntimeError(resp.text if resp.text else resp.reason)

  def del_group_user(self, grp_id:str, usr_id:str) -> None:
    resp = self.session.delete(self.api_path(f'v3/groups/{grp_id}/users/{usr_id}'))
    if resp.status_code != 204:
      raise RuntimeError(resp.text if resp.text else resp.reason)

  def domain(self, context:str|None = None) -> str:
    '''Get the domain for a given project/region/or user default'''
    if context is None:
      q = self.domains()
      for d in q:
        if d['name'] == self.session.domain_name: return d['id']
      return q[0]['id']
    q = self.projects(context)
    if len(q) == 0: raise KeyError(f'Unable to match "{context}"')
    return q[0]['domain_id']

  def domains(self) -> list:
    resp = self.session.get(self.api_path('v3/auth/domains'))
    if resp.status_code != 200 or not 'domains' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['domains']

  def get_domain_group_perms(self, domid:str, grpid:str) -> list:
    path = f'v3/domains/{domid}/groups/{grpid}/roles'
    resp = self.session.get(self.api_path(path))
    if resp.status_code != 200 or not 'roles' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['roles']

  def get_project_group_perms(self, prjid:str, grpid:str) -> list:
    path = f'v3/projects/{prjid}/groups/{grpid}/roles'
    resp = self.session.get(self.api_path(path))
    if resp.status_code != 200 or not 'roles' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['roles']

  def grant_project_group_perms(self, prjid:str, grpid:str, roleid:str):
    resp = self.session.put(self.api_path(f'v3/projects/{prjid}/groups/{grpid}/roles/{roleid}'))
    if resp.status_code != 204:
      raise RuntimeError(resp.text if resp.text else resp.reason)
  def revoke_project_group_perms(self, prjid:str, grpid:str, roleid:str):
    resp = self.session.delete(self.api_path(f'v3/projects/{prjid}/groups/{grpid}/roles/{roleid}'))
    if resp.status_code != 204:
      raise RuntimeError(resp.text if resp.text else resp.reason)

  def projects(self, name:str|None = None) -> list:
    params = dict() if name is None else { 'params': { 'name': name } }
    resp = self.session.get(self.api_path('v3/projects'), **params)
    if resp.status_code != 200 or not 'projects' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['projects']

  def get_project_details(self, prj_id:str) -> dict:
    resp = self.session.get(self.api_path(f'v3-ext/projects/{prj_id}'))
    if resp.status_code != 200 or not 'project' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['project']

  def new_project(self, name:str, parent_id:str, description:str|None = None) -> str:
    payload = {
      'name': name,
      'parent_id': parent_id,
    }
    if not description is None: payload['description'] = description
    resp = self.session.post(self.api_path('v3/projects'), json = dict(project = payload))
    if resp.status_code != 201 or not 'project' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['project']['id']

  def del_project(self, prj_id:str) -> None:
    resp = self.session.delete(self.api_path(f'v3/projects/{prj_id}'))
    if not resp.status_code in [200, 204]:
      raise RuntimeError(resp.text if resp.text else resp.reason)

  def gen_user_name(self, length = 8):
    return ''.join(random.sample(string.ascii_lowercase*length,length))
  def gen_user_password(self, length = 24):
    return ''.join(random.sample((string.ascii_lowercase + string.ascii_uppercase + string.digits)*length, length))

if __name__ == '__main__':
  import api
  import creds
  cfg = creds.creds(cloud_name = 'otc-de-iam')
  api = api.ApiSession(cfg)



  # ~ for grp in api.iam.groups():
    # ~ print('{id} {name:24} {description}'.format(**grp))
    # ~ # ic(grp)
  # ~ grpdat = api.iam.groups(name = 'admin')[0]
  # ~ for perm in api.iam.get_domain_group_perms(grpdat['domain_id'],grpdat['id']):
    # ~ print('{name:16} {type} {display_name}: {description}'.format(**perm))
    # ~ # ic(perm)

  # ~ grpdat = api.iam.groups(name = 'training2407-admin')[0]
  # ~ prjdat = api.iam.projects(name = 'eu-de_training2407')[0]
  # ~ for perm in api.iam.get_project_group_perms(prjdat['id'],grpdat['id']):
    # ~ print('{name:16} {type} {display_name}: {description}'.format(**perm))
    # ~ # ic(perm)


  del(api)


