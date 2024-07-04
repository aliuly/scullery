#!python3
#
# API sessions
#
import json
import requests

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

def http_logging(level:int = 1) -> None:
  '''Enable HTTP request logging
  
  :param level: Debug level (defaults to `1`)
  '''
  import http.client
  http.client.HTTPConnection.debuglevel = 1


class ApiSession:
  
  def __init__(self, region:str = None) -> None:
    self.region = region
  

# ~ import os
# ~ import sys

# ~ import http.client


# ~ TOKEN_CACHE_FILE = 'token.cache'

# Endpoints:
# iam.eu-de.otc.t-systems.com
# iam.eu-nl.otc.t-systems.com
endpoint = 'iam.eu-de.otc.t-systems.com'


api_url = f'https://{endpoint}/v3/auth/tokens'
reqdat = {
  'auth': {
    'identity': {
      'methods': ['password'],
      'password': {
        "user": {
          'name': creds['username'],
          'password': creds['password'],
          'domain': {
            'name': creds['user_domain_name'],
          },
        },
      },
    },
    # ~ 'scope': {
      # ~ 'project': {
        # ~ 'name': 'eu-de',
      # ~ },
    # ~ },
  },
}

response = requests.post(api_url, json=reqdat)
# ~ print(response.status_code)
# ~ print(response.headers)
# ~ print(response.json())
token = response.headers['X-Subject-Token']

###################################################################


#
# 
#
api_url = f'https://{endpoint}/v3/roles'
response = requests.get(api_url, headers = {
    'X-Auth-Token': token,
})
respdat = response.json()
print(api_url, response.status_code)
for k,v in response.headers.items(): print('\t',k,':\t',v)
# print(json.dumps(response.json(), indent=2))
for role in response.json()['roles']:
  values = {
    'description': '',
    'display_name': '',
  }
  values.update(role)
  print('{name:16} {display_name:24} {description}'.format(**values))

projname = 'eu-de_training2407'


#
# Lookup project id from a project name
#
# ~ api_url = f'https://{endpoint}/v3/projects'
# ~ response = requests.get(api_url, headers = {
    # ~ 'X-Auth-Token': token,
# ~ }, params = {
  # ~ 'name': projname,
# ~ })
# ~ respdat = response.json()
# ~ prjid = respdat['projects'][0]['id']
# ~ print('prjid',prjid)

# ~ #
# ~ # List groups
# ~ #
# ~ api_url = f'https://{endpoint}/v3/groups'
# ~ response = requests.get(api_url, headers = {
    # ~ 'X-Auth-Token': token,
# ~ })
# ~ print(response.status_code)
# ~ for k,v in response.headers.items(): print('\t',k,':\t',v)
# ~ # print(json.dumps(response.json(), indent=2))
# ~ for grp in response.json()['groups']:
  # ~ print('id={id} name={name:24} desc={description}'.format(**grp))

# ~ #
# ~ # Get group details from name
# ~ #
# ~ grpname = 'training2407-admin'
# ~ # Get group details
# ~ api_url = f'https://{endpoint}/v3/groups'
# ~ response = requests.get(api_url, headers = {
    # ~ 'X-Auth-Token': token,
# ~ }, params = {
  # ~ 'name': grpname,
# ~ })
# ~ print(api_url, response.status_code)
# ~ # for k,v in response.headers.items(): print('\t',k,':\t',v)
# ~ print(json.dumps(response.json(), indent=2))
# ~ jsdat = response.json()
# ~ grpid = jsdat['groups'][0]['id']
# ~ domid = jsdat['groups'][0]['domain_id']
# ~ print(grpname,'grpid',grpid)
# ~ print(grpname,'domid',domid)

# ~ # Get group permissions by domain
# ~ # api_url = f'https://{endpoint}/v3/OS-INHERIT/domains/{domid}/groups/{grpid}/roles/inherited_to_projects'
# ~ api_url = f'https://{endpoint}/v3/domains/{domid}/groups/{grpid}/roles'
# ~ response = requests.get(api_url, headers = {
    # ~ 'X-Auth-Token': token,
# ~ })
# ~ print(api_url, response.status_code)
# ~ for k,v in response.headers.items(): print('\t',k,':\t',v)
# ~ # print(json.dumps(response.json(), indent=2))
# ~ for grp in response.json()['groups']:
  # ~ print('id={id} name={name:24} desc={description}'.format(**grp))

# ~ # Get group permissions by project
# ~ # api_url = f'https://{endpoint}/v3/OS-INHERIT/domains/{domid}/groups/{grpid}/roles/inherited_to_projects'
# ~ api_url = f'https://{endpoint}/v3/projects/{prjid}/groups/{grpid}/roles'
# ~ response = requests.get(api_url, headers = {
    # ~ 'X-Auth-Token': token,
# ~ })
# ~ print(api_url, response.status_code)
# ~ for k,v in response.headers.items(): print('\t',k,':\t',v)
# ~ print(json.dumps(response.json(), indent=2))
# ~ # for grp in response.json()['groups']:
# ~ #  print('id={id} name={name:24} desc={description}'.format(**grp))


# ~ #
# ~ # List CUSTOM policies/roles
# ~ #
# ~ api_url = f'https://{endpoint}/v3.0/OS-ROLE/roles'
# ~ response = requests.get(api_url, headers = {
    # ~ 'X-Auth-Token': token,
# ~ })
# ~ print(response.status_code)
# ~ for k,v in response.headers.items(): print('\t',k,':\t',v)
# ~ print(response.text)
# ~ print(json.dumps(response.json(), indent=2))



api_url = f'https://{endpoint}/v3/auth/tokens'
response = requests.delete(api_url, headers = {
    'X-Auth-Token': token,
    'X-Subject-Token': token,
})
# ~ print(response.status_code)
# ~ print(response.headers)
# ~ print(response.text)



# ~ if os.path.isfile(TOKEN_CACHE_FILE):
  


# ~ curl -X GET "http://api.open-notify.org/astros.json"

# ~ response = requests.get("http://api.open-notify.org/astros.json")
# ~ print(response)
# ~ print(response.text)

