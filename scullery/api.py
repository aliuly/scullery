#!python3
#
# API sessions
#
'''REST API session implementation'''
import requests
import subprocess
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

import tcurl

from . import iam
from . import deh
from . import ecs
from . import ims
from . import tms
from . import rms

from . import obs

try:
  import minis3
  HAS_MINIS3 = True
except ImportError:
  HAS_MINIS3 = False


# ====================================================================
# Helpers
# ====================================================================

def http_logging(level: int = 1) -> None:
  '''Enable HTTP request logging

  :param level: Debug level (defaults to ``1``)
  '''
  import http.client
  http.client.HTTPConnection.debuglevel = level


def token_shutdown(url: str, token: str) -> None:
  '''INTERNAL: Handle abnormal shutdown'''
  try:
    rc = subprocess.run(['curl', '-k',
                         '-H', f'X-Auth-Token: {token}',
                         '-H', f'X-Subject-Token: {token}',
                         '-X', 'DELETE', url])
    if rc.returncode != 0:
      sys.stderr.write(f'Exit code: {rc.returncode}\n')
  except Exception as e:
    sys.stderr.write(str(e) + '\n')

# ====================================================================
# Main API session
# ====================================================================

class ApiSession:
  '''API Session
  '''

  IAM_HOST = 'iam.{region}.otc.t-systems.com'
  '''API Endpoint for creating session tokens'''
  # ------------------------------------------------------------------
  # URL helpers
  # ------------------------------------------------------------------

  def tokens_api_path(self) -> str:
    '''URL of the IAM token endpoint for the current region.'''
    api_host = ApiSession.IAM_HOST.format(region=self.region)
    return f'https://{api_host}/v3/auth/tokens'

  # ------------------------------------------------------------------
  # Constructor
  # ------------------------------------------------------------------

  def __init__(self,
      xhdrs:dict,
      region:str = None,
      project:str = None,
      clean_up:str|None = None,
  ) -> None:
    '''Create an authenticated API session.
    :param xhdrs: authentication attributes
    :param project: project for scoped sessions
    :param region: region for unscoped sessions
    :param clean_up: discard token
    '''
    self.xhdrs = xhdrs
    self.project = project
    self.region = region
    self.clean_up = clean_up

    self.region_data = None
    self.project_data = None

    # Create service clients
    self.deh = deh.Deh(self)
    self.ecs = ecs.Ecs(self)
    self.iam = iam.Iam(self)
    self.ims = ims.Ims(self)
    self.tms = tms.Tms(self)
    self.rms = rms.Rms(self)


  # ------------------------------------------------------------------
  # Cleanup
  # ------------------------------------------------------------------

  def __del__(self) -> None:
    '''Destructor — deletes the session token if one was obtained.'''
    if self.clean_up is None: return
    if sys.meta_path is None:
      sys.stderr.write('Deleting session while Python is shutting down\n')
      token_shutdown(self.tokens_api_path(), self.clean_up)
    else:
      requests.delete(self.tokens_api_path(), headers={
        'X-Auth-Token': self.clean_up,
        'X-Subject-Token': self.clean_up,
      })


  # ------------------------------------------------------------------
  # Token / project / region helpers
  # ------------------------------------------------------------------

  def project_id(self) -> str:
    '''Resolve the project ID.

    If a project name was provided at construction time, looks it up via
    the IAM API and caches the result.  Otherwise delegates to
    :meth:`region_id`.

    :returns: OpenTelekomCloud project UUID.
    :raises KeyError: If the project name cannot be resolved.
    '''
    if self.project is None: return self.region_id()
    if self.project_data is None:
      q = self.iam.projects(name=self.project)
      if len(q) != 1: raise KeyError(self.project)
      self.project_data = q[0]
    return self.project_data['id']

  def region_id(self) -> str:
    '''Resolve the region ID.

    Uses the region name (set at construction time) to look up the
    corresponding project via the IAM API.  The result is cached.

    :returns: OpenTelekomCloud project UUID for the region.
    :raises KeyError: If the region name cannot be resolved.
    '''
    if self.region_data is None:
      q = self.iam.projects(name=self.region)
      if len(q) != 1: raise KeyError(self.region)
      self.region_data = q[0]
    return self.region_data['id']


  # ------------------------------------------------------------------
  # REST helpers
  # ------------------------------------------------------------------
  def get(self, api_url, **kwargs):
    '''HTTP GET'''
    return requests.get(api_url, **self.xhdrs, **kwargs)
  def delete(self, api_url, **kwargs):
    '''HTTP DELETE'''
    return requests.delete(api_url, **self.xhdrs, **kwargs)
  def post(self, api_url, **kwargs):
    '''HTTP POST'''
    xhdrs = dict(**self.xhdrs)
    tcurl.add_headers(xhdrs,['Content-Type:application/json'])
    return requests.post(api_url, **xhdrs, **kwargs)
  def put(self, api_url, **kwargs):
    '''HTTP PUT'''
    xhdrs = dict(**self.xhdrs)
    tcurl.add_headers(xhdrs,['Content-Type:application/json'])
    return requests.put(api_url, **xhdrs, **kwargs)
  def patch(self, api_url, **kwargs):
    '''HTTP PATCH'''
    xhdrs = dict(**self.xhdrs)
    tcurl.add_headers(xhdrs,['Content-Type:application/json'])
    return requests.patch(api_url, **xhdrs, **kwargs)


class ObsSession:
  '''OBS (Object Storage Service) API session.

  Used for bucket-level operations that require AWS Signature V4 signing.
  Created by :func:`~scullery.clouds.s3session` when temporary or permanent
  AK/SK credentials are available.

  Provides the :attr:`bucket` endpoint for managing buckets and an
  :attr:`s3` endpoint (:class:`minis3.Connection`) for object-level
  operations when S3 credentials were provided.
  '''
  API_HOST = 'obs.{region}.otc.t-systems.com'
  '''OBS API endpoint template.'''

  def __init__(self,
      xhdrs:dict,
      region:str = None,
      clean_up:str|None = None,
      s3creds:dict[str,str]|None = None,
  ) -> None:
    '''Constructor.

    :param xhdrs:     Request headers (authentication).
    :param region:    OBS region (e.g. ``'eu-de'``).
    :param clean_up:  Token to revoke on destruction, or ``None``.
    :param s3creds:   Optional dict with ``access_key``, ``secret_key``,
                      and optionally ``session_token`` for :attr:`s3`.
    '''
    self.xhdrs = xhdrs
    self.region = region
    self.clean_up = clean_up

    self.bucket = obs.Buckets(self)
    if HAS_MINIS3 and s3creds:
      self.s3 = minis3.Connection(**s3creds,
          endpoint = self.api_path(),
          tls = True,
          path_style = True,
        )

  def api_path(self, path: str = '') -> str:
    '''Build the full OBS API URL for *path*.'''
    host = ObsSession.API_HOST.format(region=self.region)
    return f'https://{host}{path}'
  # ------------------------------------------------------------------
  # Cleanup
  # ------------------------------------------------------------------
  def __del__(self) -> None:
    '''Destructor — deletes the session token if one was obtained.'''
    if self.clean_up is None: return
    api_path = f'https://iam.{self.region}.otc.t-systems.com/v3/auth/tokens'
    if sys.meta_path is None:
      sys.stderr.write('Deleting session while Python is shutting down\n')
      token_shutdown(api_path, self.clean_up)
    else:
      requests.delete(api_path, headers={
        'X-Auth-Token': self.clean_up,
        'X-Subject-Token': self.clean_up,
      })

  # ------------------------------------------------------------------
  # HTTP helpers
  # ------------------------------------------------------------------

  def request(self, method: str, path: str, **kwargs):
    '''Make an OBS API request and return the response.

    :param method: HTTP method (``'get'``, ``'put'``, ``'delete'``, …)
    :param path:   URL path relative to the OBS endpoint
    :param kwargs: Forwarded to ``requests.request``
    :returns:      ``requests.Response``
    :raises requests.HTTPError: On non-2xx status
    '''
    url = self.api_path(path)
    fn = getattr(requests, method.lower())
    xhdrs = dict(**self.xhdrs)
    if 'headers' in kwargs:
      tcurl.add_headers(xhdrs, kwargs['headers'])
      del kwargs['headers']

    resp = fn(url, **xhdrs, **kwargs)
    if not resp.ok:
      raise RuntimeError(
          f'OBS API error {resp.status_code}: {resp.text[:2000]}'
      )
    return resp

if __name__ == '__main__':
  ...
