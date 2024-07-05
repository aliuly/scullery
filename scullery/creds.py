#!python3
#
#
import os
import yaml

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

import consts as K

class STR:
  '''String constants for this module'''
  ENV_PREFIX = 'OS_'
  OS_CONFIG_FILE = 'OS_CLIENT_CONFIG_FILE'
  HOME = 'HOME'

  OS_CFG_HOME = '.config/openstack'
  ETC_CFG = '/etc/openstack'
  CLOUDS_YAML = 'clouds.yaml'
  SECURE_YAML = 'secure.yaml'

  CLOUDS = 'clouds'
  AUTH = 'auth'

  USER_DOMAIN_NAME = 'user_domain_name'
  USERNAME = 'username'
  PASSWORD = 'password'
  PROJECT_NAME = 'project_name'

  REGION_NAME = 'region_name'
attributes = [
  STR.USER_DOMAIN_NAME,
  STR.USERNAME,
  STR.PASSWORD,
  STR.PROJECT_NAME,
]
'''List of params needed to authenticate'''


def get_env_creds() -> dict:
  '''Configure credentials from environment variables

  :returns dict: containing login credentials
  '''
  creds = dict()
  for attr in attributes:
    ky = STR.ENV_PREFIX + attr.upper()
    if not ky in os.environ: continue
    creds[attr] = os.environ[ky]
  return creds

def check_kwargs(opts:dict) -> bool:
  '''Test that dictionary contains complete credentials

  :param opts: dictionary containing credentials
  :returns: True if credentials are complete, False otherwise
  '''
  for arg in attributes:
    if not arg in opts: return False
  return True

def creds(cloud_name:str|None = None, **kwargs) -> dict:
  '''Get configured login credentials

  :param cloud_name: Name of the cloud to connect to
  :param kwargs: Optionally, specify login credentials as named arguments
  :returns: dictionary containing credentials

  Follow the OpenStack/OTC SDK conventions on how to configure clouds
  '''
  if check_kwargs(kwargs): return kwargs
  env_creds = get_env_creds()
  if check_kwargs(env_creds): return env_creds

  cloud_yamls = []
  if STR.OS_CONFIG_FILE in os.environ: cloud_yamls.append(os.environ[STR.OS_CONFIG_FILE])
  cloud_yamls.append(STR.CLOUDS_YAML)
  if STR.HOME in os.environ:
    cloud_yamls.append(os.path.join(os.environ[STR.HOME],STR.OS_CFG_HOME,STR.CLOUDS_YAML))
  cloud_yamls.append(os.path.join(STR.ETC_CFG,STR.CLOUDS_YAML))

  if cloud_name is None:  raise ValueError('No parameter "cloud_name" specified')

  for cfgfile in cloud_yamls:
    if not os.path.isfile(cfgfile): continue
    with open(cfgfile, 'r') as fp:
      ydat = yaml.safe_load(fp)
    if not (STR.CLOUDS in ydat and cloud_name in ydat[STR.CLOUDS] and STR.AUTH in ydat[STR.CLOUDS][cloud_name]): continue
    kwargs = ydat[STR.CLOUDS][cloud_name][STR.AUTH]
    # If no project_name but there is a region_name, use that...
    if not STR.PROJECT_NAME in kwargs and STR.REGION_NAME in ydat[STR.CLOUDS][cloud_name]:
      kwargs[STR.PROJECT_NAME] = ydat[STR.CLOUDS][cloud_name][STR.REGION_NAME]
    if os.path.basename(cfgfile) == STR.CLOUDS_YAML:
      secure_yaml = os.path.join(os.path.dirname(cfgfile),STR.SECURE_YAML)
      if os.path.isfile(secure_yaml):
        with open(secure_yaml, 'r') as fp:
          ydat = yaml.safe_load(fp)
        if STR.CLOUDS in ydat and cloud_name in ydat[STR.CLOUDS] and STR.AUTH in ydat[STR.CLOUDS][cloud_name]:
          kwargs.update(ydat[STR.CLOUDS][cloud_name][STR.AUTH])
    if check_kwargs(kwargs): return kwargs

  raise ValueError('No configuration found')

if __name__ == '__main__':
  args = creds(cloud_name = 'otc-de-iam')
  ic(args)
