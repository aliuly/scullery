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

ENV_PREFIX = 'OS_'

attributes = [
  'user_domain_name',
  'username',
  'password',
  'project_name',
]
'''List of params needed to authenticate'''


def get_env_creds() -> dict:
  '''Configure credentials from environment variables
  
  :returns dict: containing login credentials
  '''
  creds = dict()
  for attr in attributes:
    ky = ENV_PREFIX + attr.upper()
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
  if K.OS_CONFIG_FILE in os.environ: cloud_yamls.append(os.environ[K.OS_CONFIG_FILE])
  cloud_yamls.append('clouds.yaml')
  if K.HOME in os.environ:
    cloud_yamls.append(os.path.join(os.environ[K.HOME],'.config/openstack','clouds.yaml'))
  cloud_yamls.append('/etc/openstack/clouds.yaml')
  
  if cloud_name is None:  raise ValueError('Must specify "cloud_name"')

  for cfgfile in cloud_yamls:
    if not os.path.isfile(cfgfile): continue
    with open(cfgfile, 'r') as fp:
      ydat = yaml.safe_load(fp)
    if not ('clouds' in ydat and cloud_name in ydat['clouds'] and 'auth' in ydat['clouds'][cloud_name]): continue
    kwargs = ydat['clouds'][cloud_name]['auth']
    if os.path.basename(cfgfile) == 'clouds.yaml':
      secure_yaml = os.path.join(os.path.dirname(cfgfile),'secure.yaml')
      if os.path.isfile(secure_yaml):
        with open(secure_yaml, 'r') as fp:
          ydat = yaml.safe_load(fp)
        if 'clouds' in ydat and cloud_name in ydat['clouds'] and 'auth' in ydat['clouds'][cloud_name]:
          kwargs.update(ydat['clouds'][cloud_name]['auth'])
    if check_kwargs(kwargs): return kwargs
  
  raise ValueError('No configuration found')
  
if __name__ == '__main__':
  args = creds(cloud_name = 'otc-iam')
  ic(args)
