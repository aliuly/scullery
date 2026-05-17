#
# Configure s3cmd
#
import os
import pathlib
import shutil
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from configupdater import ConfigUpdater

def update(ak:str|None = '', sk:str|None = '', session:str|None = None, region:str|None = None, s3file:str|None = None) -> bool:
  '''Update S3 config file

  :param ak: access_key
  :param sk: secret_key
  :param session: optional session token (for temp AK/SK)
  :param region: optional region (only used if the file does not exist)
  :param s3file: file to update (defaults to `$HOME/.s3cfg`)
  :returns: True if file was changed, otherwise False
  '''
  if s3file is None:
    # Update ~/.s3cfg
    s3file = os.path.join(pathlib.Path.home(),'.s3cfg')

  try:
    with open(s3file) as fp:
      inp = fp.read()
  except FileNotFoundError:
    inp = (
          '[default]\n'
          'bucket_location = {region}\n'
          'check_ssl_certificate = True\n'
          'check_ssl_hostname = True\n'
          'host_base = obs.{region}.otc.t-systems.com\n'
          'host_bucket = %(bucket)s.obs.{region}.otc.t-systems.com\n'
          'signature_v2 = False\n'
          'use_https = True\n'
    ).format(region = 'eu-de' if region is None else region)

  updater = ConfigUpdater()
  updater.read_string(inp)

  def vcheck(key:str, val:str|None):
    if val == '': return  # No change...
    if val is None:
      if key in updater['default']: del updater['default'][key]
    else:
      updater['default'][key] = val

  vcheck('access_key', ak)
  vcheck('secret_key', sk)
  vcheck('access_token', session)
  if region is not None:
    updater['default']['bucket_location'] = region
    updater['default']['host_base'] = 'obs.{region}.otc.t-systems.com'.format(region = region)
    updater['default']['host_bucket'] = '%(bucket)s.obs.{region}.otc.t-systems.com'.format(region = region)

  if str(updater) != inp:
    sys.stderr.write(f'Backing up to {s3file}.backup\n')
    shutil.copy2(s3file, s3file + '.backup')
    sys.stderr.write(f'Updating {s3file}\n')
    with open(s3file,'w') as fp:
      updater.write(fp)
    return True
  return False

if __name__ == '__main__':
  update('AKTEXT','SKTEXT')

