#
# Cloud credential resolution
#
'''Cloud credential resolution and session creation.

Resolves credentials from command-line arguments, environment variables,
and ``clouds.yaml`` / ``secure.yaml`` configuration files.  Provides
:func:`session` for standard API sessions and :func:`s3session` for
OBS (S3-compatible) sessions with AK/SK signing.

See :doc:`../config` for the full configuration reference.
'''
import argparse
import datetime
import os
import pathlib
import requests
import sys
import yaml
from typing import Any

from mypielib.get_nested import get_nested_value
import tcurl

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from . import __meta__
from . import api

DEFAULT_REGION = 'eu-de'
'''Default region to use'''

yaml_files = []
def read_yaml(filepath:str) -> bool:
  '''Read and parse a YAML configuration file.

  Appends ``(filepath, parsed_dict)`` to the global :data:`yaml_files`
  list on success.

  :param filepath: Path to the YAML file.
  :returns: ``True`` on success, ``False`` if the file doesn't exist
            or cannot be parsed.
  '''
  if not os.path.isfile(filepath): return False
  try:
    with open(filepath) as fp:
      y = yaml.safe_load(fp)
    if isinstance(y,dict):
      yaml_files.append([filepath,y])
    return True
  except Exception as e:
    sys.stderr.write(f'Ignoring {filepath}: {e}\n')
  return False

def resolve_from_yaml(keypath:str) -> Any:
  '''Walk the parsed YAML files and return the first matching value.

  Lazily loads YAML files (``secure.yaml`` then ``clouds.yaml``) from
  the standard search paths on first call.

  :param keypath: Dotted key path, e.g. ``'clouds.scullery.auth.username'``.
  :returns: A tuple ``(value, source_filepath)`` or ``(None, None)`` if
            the key is not found in any file.
  '''
  if not yaml_files:
    for p in [
        'secure.yaml', 'clouds.yaml',
        os.path.join(pathlib.Path.home(), '.config/openstack/secure.yaml'),
        os.path.join(pathlib.Path.home(), '.config/openstack/clouds.yaml'),
        '/etc/openstack/secure.yaml',
        '/etc/openstack/clouds.yaml',
    ]:
      read_yaml(p)
    yaml_files.append(['',{}]) # Make it so we don't try to read YAML files again
  for fp,y in yaml_files:
    try:
      value = get_nested_value(keypath,y)
      return value, fp
    except KeyError:
      continue
  return None, None

def resolve_creds(
        args:argparse.Namespace|None = None,
  ) -> dict[str,str]|None:
  '''Resolve credentials...
  :param args: passed command line arguments
  :returns: dict with usable crednetials
  '''
  creds = {
    'token': None,
    'ak': None,
    'sk': None,
    'securitytoken': None,
    'username': None,
    'password': None,
    'user_domain_name': None,
    'project': None,
    'region': None,
  }
  myname = __meta__.name

  if hasattr(args,'project') and getattr(args,'project') is not None:
    creds['project'] = getattr(args,'project')
    creds['region']  = creds['project'].split('_',1)[0]
  elif hasattr(args,'region') and getattr(args,'region') is not None:
    creds['region'] = getattr(args,'region')
  else:
    creds['region'] = DEFAULT_REGION

  inargs = dict()
  for k in creds:
    if hasattr(args,k):
      inargs[k] = getattr(args,k)
    else:
      inargs[k] = None

  if inargs['token'] is not None:
    # OK, uses a token...
    creds['token'] = inargs['token']
    return creds
  elif inargs['ak'] is not None and inargs['sk'] is not None:
    # It is using AK/SK credentials
    creds['ak'] = inargs['ak']
    creds['sk'] = inargs['sk']
    creds['securitytoken'] = inargs['securitytoken']
    return creds
  elif inargs['username'] is not None and inargs['password'] is not None:
    # Username and password provided... Is there a domain name?
    if inargs['user_domain_name'] is not None:
      creds['username'] = inargs['username']
      creds['password'] = inargs['password']
      creds['user_domain_name'] = inargs['user_domain_name']
      return creds
    elif 'OS_USER_DOMAIN_NAME' in os.environ:
      creds['username'] = inargs['username']
      creds['password'] = inargs['password']
      creds['user_domain_name'] = os.environ['OS_USER_DOMAIN_NAME']
      return creds
    elif (domain := resolve_from_yaml(f'clouds.{myname}.auth.user_domain_name'))[0] is not None:
      sys.stderr.write(f'Using domain {domain[0]} from "{domain[1]}\n')
      creds['username'] = inargs['username']
      creds['password'] = inargs['password']
      creds['user_domain_name'] = domain[0]
      return creds

  # Nothing so far... check environment variables
  now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
  # ~ ic(now)
  if 'OS_AUTH_TOKEN' in os.environ:
    # OK, it was created by tcurl...
    if 'OS_AUTH_EXPIRES_AT' in os.environ:
      if now < os.environ['OS_AUTH_EXPIRES_AT']:
        if 'OS_AUTH_PROJECT_ID' in os.environ:
          if inargs['project'] is not None:
            # OK, we want a scoped token, assuming this is OK...
            sys.stderr.write('Using "OS_AUTH_TOKEN" enviroment variable\n')
            creds['token'] = os.environ['OS_AUTH_TOKEN']
            return creds
          sys.stderr.write('Ignoring environment variable "OS_AUTH_TOKEN", scoped token when unscoped token requested\n')
        elif (('OS_AUTH_USER_ID' in os.environ) or ('OS_AUTH_DOMAIN_ID' in os.environ)):
          # It should be an unscoped token...
          sys.stderr.write('Using "OS_AUTH_TOKEN" enviroment variable\n')
          creds['token'] = os.environ['OS_AUTH_TOKEN']
          return creds
        else:
          # We don't know if it is scoped or not...
          sys.stderr.write('Using "OS_AUTH_TOKEN" enviroment variable\n')
          creds['token'] = os.environ['OS_AUTH_TOKEN']
          return creds
      else:
        sys.stderr.write('Ignoring environment "OS_AUTH_TOKEN" is already expired\n')
    else: #
      sys.stderr.write('Using unvalidated "OS_AUTH_TOKEN" environment variable\n')
      creds['token'] = os.environ['OS_AUTH_TOKEN']
      return creds
  if 'OS_TOKEN' in os.environ:
    sys.stderr.write('Using "OS_TOKEN" environment variable\n')
    creds['token'] = os.environ['OS_TOKEN']
    return creds

  if 'OS_ACCESS_KEY' in os.environ and 'OS_SECRET_KEY' in os.environ:
    if 'OS_AKSK_EXPIRES_AT' in os.environ and 'OS_SECURITY_TOKEN' in os.environ:
      if now < os.environ['OS_AUTH_EXPIRES_AT']:
        sys.stderr.write('Using temporary AK/SK credentials from environment\n')
        creds['ak'] = os.environ['OS_ACCESS_KEY']
        creds['sk'] = os.environ['OS_SECRET_KEY']
        creds['securitytoken'] = os.environ['OS_SECURITY_TOKEN']
        return creds
      else:
        sys.stderr.write('Ignoring expried AK/SK environment variables\n')
    else:
      creds['ak'] = os.environ['OS_ACCESS_KEY']
      creds['sk'] = os.environ['OS_SECRET_KEY']
      if 'OS_SECURITY_TOKEN' in os.environ:
        sys.stderr.write('Using temporary AK/SK credentials from environment\n')
        creds['securitytoken'] = os.environ['OS_SECURITY_TOKEN']
      else:
        sys.stderr.write('Using permanent AK/SK credentials from environment\n')
      return creds

  if 'OS_USERNAME' in os.environ and 'OS_PASSWORD' in os.environ:
    # Username and password provided... Is there a domain name?
    if 'OS_USER_DOMAIN_NAME' in os.environ:
      creds['username'] = os.environ['OS_USERNAME']
      creds['password'] = os.environ['OS_PASSWORD']
      creds['user_domain_name'] = os.environ['OS_USER_DOMAIN_NAME']
      return creds
    elif (domain := resolve_from_yaml(f'clouds.{myname}.auth.user_domain_name'))[0] is not None:
      sys.stderr.write(f'Using domain {domain[0]} from "{domain[1]}\n')
      creds['username'] = os.environ['OS_USERNAME']
      creds['password'] = os.environ['OS_PASSWORD']
      creds['user_domain_name'] = domain[0]
      return creds
    else:
      sys.stderr.write('Missing OS_USER_DOMAIN_NAME, ignoring OS_USERNAME+OS_PASSWORD\n')

  # First check if we have valid cached credentials
  token, tk_file = resolve_from_yaml(f'clouds.{myname}.cached.token')
  expires_at, _ = resolve_from_yaml(f'clouds.{myname}.cached.expires_at')
  domain_id, _ = resolve_from_yaml(f'clouds.{myname}.cached.domain_id')
  if token is not None and expires_at is not None and domain_id is not None:
    if now < expires_at:
      sys.stderr.write(f'Using token from {tk_file}\n')
      creds['token'] = token
      creds['domain_id'] = domain_id
      return creds
    else:
      sys.stderr.write(f'Ignoring expired token in {tk_file}\n')

  # Check if we have valid AK/SK cached credentials
  ak,ak_file = resolve_from_yaml(f'clouds.{myname}.cached.ak')
  sk,_ = resolve_from_yaml(f'clouds.{myname}.cached.sk')
  session, _ = resolve_from_yaml(f'clouds.{myname}.cached.securitytoken')
  expires_at, _ = resolve_from_yaml(f'clouds.{myname}.cached.expires_at')
  domain_id, _ = resolve_from_yaml(f'clouds.{myname}.cached.domain_id')
  if ak is not None and sk is not None and session is not None and expires_at is not None and domain_id is not None:
    if now < expires_at:
      creds['ak'] = ak
      creds['sk'] = sk
      creds['securitytoken'] = session
      creds['domain_id'] = domain_id
      sys.stderr.write(f'Using Temp AK/SK from {ak_file}\n')
      return creds
    else:
      sys.stderr.write(f'Ignoring expired temp AK/SK credentials in {ak_file}\n')

  # OK, we are using files
  ak,ak_file = resolve_from_yaml(f'clouds.{myname}.ak')
  sk,sk_file = resolve_from_yaml(f'clouds.{myname}.sk')
  if ak is not None and sk is not None:
    sys.stderr.write(f'Using AK from {ak_file} and SK from {sk_file}\n')
    creds['ak'] = ak
    creds['sk'] = sk
    return creds

  # Username+password...
  files = dict()
  count = 0
  for i in ['username','password','user_domain_name']:
    k, f = resolve_from_yaml(f'clouds.{myname}.auth.{i}')
    if k is None: continue
    count += 1
    files[f] = f
    creds[i] = k
  if count == 3:
    sys.stderr.write(f'Using username+password from {", ".join(files.keys())}\n')
    return creds

  # OK no good credentials found
  return None

def token_details(token:str, region:str) -> dict[str,Any]:
  # Check the type of token we are using...
  xhdrs = tcurl.creds(token = token)
  tcurl.add_headers(xhdrs,[f'X-Subject-Token:{token}'])
  resp = requests.get(f'https://iam.{region}.otc.t-systems.com/v3/auth/tokens',
        **xhdrs)
  if resp.status_code != 200:
    raise RuntimeError(resp.text)
  return resp.json()['token']

def s3session(args:argparse.Namespace) -> api.ObsSession:
  '''Initialize an S3/OBS session
  :param args: Command line arguments
  :returns: initialized session
  '''
  if args.project is not None:
    args.region = args.project.split('_')[0]
    args.project = None
    sys.stderr.write(f's3sessions are not project scoped Using {args.region}\n')
  creds = resolve_creds(args=args)
  if creds is None:
    raise PermissionError('No valid credentials')

  clean_up = None
  xhdrs = None

  region = creds['region']
  if creds['token'] is not None:
    token = creds['token']
  elif creds['ak'] is not None and creds['sk'] is not None:
    token = None
  elif creds['username'] is not None and creds['password'] is not None and creds['user_domain_name'] is not None:
    # Issue token and  arrange for token revokation
    token, details = tcurl.login(
          username = creds['username'],
          password = creds['password'],
          domain = creds['user_domain_name'],
          project = creds['project'],
          region = creds['region'],
    )
    clean_up = token
  else:
    raise ValueError('Improper or malformed credentials')

  if token is not None:
    creds = tcurl.temp_aksk(
          region = region,
          token = token,
    )
    creds['ak'] = creds['access']
    creds['sk'] = creds['secret']
  xhdrs = tcurl.creds(
          ak = creds['ak'],
          sk = creds['sk'],
          securitytoken = creds['securitytoken'],
          awsv4_region = region,
  )
  return api.ObsSession(
        xhdrs = xhdrs,
        region = region,
        clean_up = clean_up,
  )

def session(
    args:argparse.Namespace,
    scoped:bool=False,
  ) -> api.ApiSession:
  '''Initialize a session
  :param args: Command line arguments
  :param scoped: Force a session scope
  :returns: initialized session
  '''
  if scoped and args.project is None:
    args.project = DEFAULT_REGION if args.region is None else args.region

  creds = resolve_creds(args=args)
  if creds is None:
    raise PermissionError('No valid credentials')

  # ~ ic(creds)
  clean_up = None
  if creds['token'] is not None:
    # OK, we are using a token.
    details = token_details(creds['token'], creds['region'])
    if args.project is None:
      # OK, unscoped token needed...
      if 'project' in details:
        # Oh, no, this is a scoped token! ABORT!
        raise ValueError('Scoped token provided while Unscoped requested')
      # Otherwise, we assume unscoped!
      token = creds['token']
    else:
      # OK, scoped token needed.
      if 'project' in details:
        # Check if the project scope matches
        if details['project']['name'] != args.project:
          # Scoped to the wrong project!
          raise ValueError(f'Scope mismatch, required: {args.project}, provided {details["project"]["name"]}')
        token = creds['token']
      else:
        # Assuming Unscoped token provided... re-issue with the right scope...
        sys.stderr.write(f'Re-issuing scoped token for {args.project}\n')
        token, _ = tcurl.login(
            token = creds['token'],
            project = args.project,
        )
        clean_up = token
    xhdrs = tcurl.creds(token = token)
  elif creds['ak'] is not None and creds['sk'] is not None:
    # Save it but also look-up region or project
    xhdrs = tcurl.creds(
          ak = creds['ak'],
          sk = creds['sk'],
          securitytoken = creds['securitytoken']
    )
    if creds['project'] is not None: # Project scope
      project_id = tcurl.project_lookup(creds['project'], xhdrs, None)
      if project_id is None: raise KeyError(args.project_name)
      tcurl.add_project_id(xhdrs, project_id)
    else: # Unscoped...
      try:
        domain_id, _ = tcurl.ak_domain_lookup(creds['ak'], xhdrs, None)
        tcurl.add_domain_id(xhdrs, domain_id)
      except requests.exceptions.HTTPError as err:
        sys.stderr.write(f'Error looking-up domain_id: {err}\n')
  elif creds['username'] is not None and creds['password'] is not None and creds['user_domain_name'] is not None:
    # Issue token and  arrange for token revokation
    token, details = tcurl.login(
          username = creds['username'],
          password = creds['password'],
          domain = creds['user_domain_name'],
          project = creds['project'],
          region = creds['region'],
    )
    xhdrs = tcurl.creds(token = token)
    clean_up = token
  else:
    raise ValueError('Improper or malformed credentials')

  return api.ApiSession(
        xhdrs = xhdrs,
        region = creds['region'],
        project = creds['project'],
        clean_up = clean_up,
  )

if __name__ == '__main__':
  ...
