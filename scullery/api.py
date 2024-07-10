#!python3
#
# API sessions
#
'''REST API session implementation'''
import json
import os
import platform
import requests
import shlex
import subprocess
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

import iam
import tms
import rms

from creds import STR as CRSTR

def http_logging(level:int = 1) -> None:
  '''Enable HTTP request logging

  :param level: Debug level (defaults to `1`)
  '''
  import http.client
  http.client.HTTPConnection.debuglevel = level

def token_shutdown_posix(url:str, token:str) -> None:
  '''INTERNAL: Handle abnormal shutdown on POSIX systems'''
  os.system(shlex.join(['curl', '-k',
                      '-H', f'X-Auth-Token: {token}',
                      '-H', f'X-Subject-Token: {token}',
                      '-X', 'DELETE',
                      url]))

def token_shutdown_win(url:str, token:str) -> None:
  '''INTERNAL: Handle abnormal shutdown on non-POSIX systems'''
  try:
    rc = subprocess.run(['curl', '-k',
                      '-H', f'X-Auth-Token: {token}',
                      '-H', f'X-Subject-Token: {token}',
                      '-X', 'DELETE',
                      url])
    if rc.returncode != 0: sys.stderr.write(f'Exit code: {rc.returncode}\n')
  except Exception as e:
    sys.stderr.write(str(e)+'\n')

if os.name == 'posix':
  token_shutdown = token_shutdown_posix
else:
  token_shutdown = token_shutdown_win

class ApiSession:
  '''API Session class'''
  IAM_HOST = 'iam.{region}.otc.t-systems.com'
  '''API Endpoint for creating session tokens'''

  def tokens_api_path(self) -> str:
    '''API URL path'''
    api_host = ApiSession.IAM_HOST.format(region = self.region)
    return f'https://{api_host}/v3/auth/tokens'

  def __init__(self, creds:dict) -> None:
    '''Constructor

    :param creds: Contain session credentials

    Will get a session token using REST API using the given
    credentials
    '''
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
      self.project_name = creds[CRSTR.PROJECT_NAME]
    else:
      self.region = creds[CRSTR.PROJECT_NAME]
      self.project_name = None
    self.user_name = creds[CRSTR.USERNAME]
    self.domain_name = creds[CRSTR.USER_DOMAIN_NAME]
    self.cloud_name = creds[CRSTR.CLOUD_NAME] if CRSTR.CLOUD_NAME in creds else None

    response = requests.post(self.tokens_api_path(), json = jsdat)
    if response.status_code != 201 or not 'X-Subject-Token' in response.headers:
      # Authentication...
      raise PermissionError(response.text)

    self.token = response.headers['X-Subject-Token']
    self.iam = iam.Iam(self)
    self.tms = tms.Tms(self)
    self.rms = rms.Rms(self)

  def __del__(self) -> None:
    '''Destructor

    Deletes the created session token
    '''
    if not self.token is None:
      if sys.meta_path is None:
        sys.stderr.write('Deleting session while Python is shutting down\n')
        token_shutdown(self.tokens_api_path(), self.token)
      else:
        response = requests.delete(self.tokens_api_path(), headers = {
            'X-Auth-Token': self.token,
            'X-Subject-Token': self.token,
        })

  def get(self, api_url, **kwargs):
    '''REST API `get` method

    :param api_url: URL for REST API
    :param **kwargs: additional params as needed by REST API
    '''
    return requests.get(api_url, **kwargs, headers = {
            'X-Auth-Token': self.token,
        })
  def post(self, api_url, **kwargs):
    '''REST API `post` method

    :param api_url: URL for REST API
    :param **kwargs: additional params as needed by REST API
    '''
    return requests.post(api_url, **kwargs, headers = {
            'X-Auth-Token': self.token,
        })
  def delete(self, api_url, **kwargs):
    '''REST API `delete` method

    :param api_url: URL for REST API
    :param **kwargs: additional params as needed by REST API
    '''
    return requests.delete(api_url, **kwargs, headers = {
            'X-Auth-Token': self.token,
        })

  def put(self, api_url, **kwargs):
    '''REST API `put` method

    :param api_url: URL for REST API
    :param **kwargs: additional params as needed by REST API
    '''
    return requests.put(api_url, **kwargs, headers = {
            'X-Auth-Token': self.token,
        })

if __name__ == '__main__':
  import creds
  cfg = creds.creds(cloud_name = 'otc-de-iam')
  api = ApiSession(cfg)
  ic(api)
  # ~ del(api)
