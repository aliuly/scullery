#!python3
#
# API sessions
#

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

if __name__ == '__main__':
  import api
  import creds
  cfg = creds.creds(cloud_name = 'otc-de-iam')
  api = api.ApiSession(cfg)


  # ~ de_id = api.iam.projects(name = 'eu-de')[0]['id']
  # ~ new_id = api.iam.new_project(name = 'eu-de_onetwo', parent_id = de_id, description = 'Test project')
  # ~ prj_dat = api.iam.get_project_details(new_id)
  # ~ ic(prj_dat)

  # ~ api.iam.del_project(prj_id = new_id)

  # ~ prj_id = None
  # ~ for prj in api.iam.projects():
    # ~ print('{id} {name}'.format(**prj))
    # ~ if '_' in prj['name']: prj_id = prj['id']
    # ~ # ic(prj)
  # ~ if not prj_id is None:
    # ~ prj_dat = api.iam.get_project_details(prj_id)
    # ~ ic(prj_dat)
  # ~ print('=')
  # ~ for prj in api.iam.projects(name = 'eu-de_training2407'):
    # ~ ic(prj)

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


  # TODO:
  # Add domain permissions: https://docs.otc.t-systems.com/identity-access-management/api-ref/apis/permission_management/granting_permissions_to_a_user_group_of_a_domain.html
  # Add project permissions: https://docs.otc.t-systems.com/identity-access-management/api-ref/apis/permission_management/granting_permissions_to_a_user_group_corresponding_to_a_project.html
  # Add user to group: https://docs.otc.t-systems.com/identity-access-management/api-ref/apis/user_group_management/adding_a_user_to_a_user_group.html
  # Remove user from group? https://docs.otc.t-systems.com/identity-access-management/api-ref/apis/user_management/deleting_a_user_from_a_user_group.html
  # User operations:
  #   list users: https://docs.otc.t-systems.com/identity-access-management/api-ref/apis/user_management/querying_a_user_list.html#en-us-topic-0057845638
  #   new user: https://docs.otc.t-systems.com/identity-access-management/api-ref/apis/user_management/creating_a_user.html
  #   del user: https://docs.otc.t-systems.com/identity-access-management/api-ref/apis/user_management/deleting_a_user.html


  del(api)


