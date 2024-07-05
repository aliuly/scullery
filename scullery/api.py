#!python3
#
# API sessions
#
import json
import requests
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

import iam

from creds import STR as CRSTR

def http_logging(level:int = 1) -> None:
  '''Enable HTTP request logging

  :param level: Debug level (defaults to `1`)
  '''
  import http.client
  http.client.HTTPConnection.debuglevel = 1


class ApiSession:
  IAM_HOST = 'iam.{region}.otc.t-systems.com'

  def tokens_api_path(self) -> str:
    api_host = ApiSession.IAM_HOST.format(region = self.region)
    return f'https://{api_host}/v3/auth/tokens'

  def __init__(self, creds:dict) -> None:
    self.token = None
    jsdat = {
        'auth': {
          'identity': {
            'methods': ['password'],
            'password': {
              "user": {
                'name': creds[CRSTR.USERNAME],
                'password': creds[CRSTR.PASSWORD],
                'domain': {
                  'name': creds[CRSTR.USER_DOMAIN_NAME],
                },
              },
            },
          },
        },
      }
    if '_' in creds[CRSTR.PROJECT_NAME]:
      # We need to scope the token
      self.region = creds[CRSTR.PROJECT_NAME].split('_',1)[0]
      jsdat['auth']['scope'] = {
        'project': {
          'name': creds[CRSTR.PROJECT_NAME]
        }
      }
    else:
      self.region = creds[CRSTR.PROJECT_NAME]

    response = requests.post(self.tokens_api_path(), json = jsdat)
    if response.status_code != 201 or not 'X-Subject-Token' in response.headers:
      # Authentication...
      raise PermissionError(response.text)

    self.token = response.headers['X-Subject-Token']
    self.iam = iam.Iam(self)

  def __del__(self) -> None:
    if not self.token is None:
      if sys.meta_path is None:
        sys.stderr.write('Error deleting session... Python is shutting down\n')
      else:
        response = requests.delete(self.tokens_api_path(), headers = {
            'X-Auth-Token': self.token,
            'X-Subject-Token': self.token,
        })

  def get(self, api_url, **kwargs):
    return requests.get(api_url, **kwargs, headers = {
            'X-Auth-Token': self.token,
        })
  def post(self, api_url, **kwargs):
    return requests.post(api_url, **kwargs, headers = {
            'X-Auth-Token': self.token,
        })
  def delete(self, api_url, **kwargs):
    return requests.delete(api_url, **kwargs, headers = {
            'X-Auth-Token': self.token,
        })



if __name__ == '__main__':
  import creds
  cfg = creds.creds(cloud_name = 'otc-de-iam')
  api = ApiSession(cfg)
  ic(api)
  del(api)
