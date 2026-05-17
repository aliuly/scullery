#
# Login interface
#
'''
Lets you issue temporary credentials at the start of a session.

TODO: update ~/s3cfg

This can issue temp AK/SK and unscoped tokens.  Tokens is the
default as temp AK/SK has these issues:

* No IAM access
* No TMS access (probably other global services too)

temp AK/SK works well for:

* OBS access
* Project scoped requests
* Project info

'''
import argparse
import io
import os
import pathlib
import shutil
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from ruamel.yaml import YAML
import tcurl_login
import tcurl

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from . import clouds
from . import parsers
from . import s3cfg
from . import __meta__


def logout(args: argparse.Namespace) -> None:
  '''Logout recipe'''
  yaml = YAML()
  for fpath in ['clouds.yaml',os.path.join(pathlib.Path.home(),'.config/openstack/clouds.yaml') ]:
    if os.path.isfile(fpath): break
  try:
    with open(fpath) as fp:
      inp = fp.read()
    code = yaml.load(inp)
  except FileNotFoundError:
    code = {
      'clouds': {
        __meta__.name: dict(),
      }
    }
  if ('clouds' not in code
        or __meta__.name not in code['clouds']
        or 'cached' not in code['clouds'][__meta__.name]
  ):
    sys.stderr.write('No cached credentials found\n')
    return
  cached = code['clouds'][__meta__.name]['cached']
  del code['clouds'][__meta__.name]['cached']

  # Check if we oughta delete the token...
  if 'token' in cached:
    region = cached.get('region', 'eu-de')
    try:
      tcurl.logout(region = region, token = cached['token'])
    except Exception as e:
      sys.stderr.write(f'Logout error: {e}\n')

  out = io.StringIO()
  yaml.dump(code, out)
  if out.getvalue() != inp:
    # Create a backup...
    backup_file = (fpath[:-5] if fpath.endswith('.yaml') else fpath) + '.old'
    sys.stderr.write(f'Backing up to {backup_file}\n')
    shutil.copy2(fpath, backup_file)
    sys.stderr.write(f'Updating {fpath}\n')
    with open(fpath, 'w') as fp:
      fp.write(out.getvalue())

    if 'ak' in cached and args.s3cfg: s3cfg.update(None, None)


def login(args: argparse.Namespace) -> None:
  '''Login recipe'''
  if args.s3cfg and not args.aksk:
    sys.stderr.write('`--s3cfg` can only specified with `--aksk`\n')
    sys.exit(1)

  yaml = YAML()
  for fpath in ['clouds.yaml',os.path.join(pathlib.Path.home(),'.config/openstack/clouds.yaml') ]:
    if os.path.isfile(fpath): break

  try:
    with open(fpath) as fp:
      inp = fp.read()
    code = yaml.load(inp)
  except FileNotFoundError:
    code = {
      'clouds': {
        __meta__.name: dict(),
      }
    }
  if 'clouds' not in code: code['clouds'] = dict()
  if __meta__.name not in code['clouds']: code['clouds'][__meta__.name] = dict()

  creds = tcurl_login.get_credentials(defaults = code['clouds'][__meta__.name].get('auth'))
  if not creds:
    sys.stderr.write('Cancelled by user\n')
    exit()

  # Issue unscoped token
  token, details = tcurl.login(
      username = creds['username'],
      password = creds['password'],
      domain = creds['domain'],
      totp = creds['otp'],
      region = args.region,
  )
  if args.aksk:
    # Issue temp AK/SK
    aksk = tcurl.temp_aksk(region = args.region, token = token, max_secs = args.ttl)
    ic(aksk)
    code['clouds'][__meta__.name]['cached'] = {
        'ak': aksk['access'],
        'sk': aksk['secret'],
        'securitytoken': aksk['securitytoken'],
        'expires_at': aksk['expires_at'],
        'domain_id':  details['domain']['id'],
        'user_id': details['user']['id'],
    }
    # We can now delete the token...
    tcurl.logout(region = args.region, token = token)
  else:
    # Cache the unscoped token
    code['clouds'][__meta__.name]['cached'] = {
      'token': token,
      'expires_at': details['expires_at'],
      'region': args.region,
      'domain_id':  details['domain']['id'],
      'user_id': details['user']['id'],
    }

  out = io.StringIO()
  yaml.dump(code, out)
  if out.getvalue() != inp:
    # Create a backup...
    backup_file = (fpath[:-5] if fpath.endswith('.yaml') else fpath) + '.old'
    sys.stderr.write(f'Backing up to {backup_file}\n')
    shutil.copy2(fpath, backup_file)
    sys.stderr.write(f'Updating {fpath}\n')
    with open(fpath, 'w') as fp:
      fp.write(out.getvalue())
    if args.s3cfg:
      s3cfg.update(
          aksk['access'],
          aksk['secret'],
          aksk['securitytoken'],
          args.region,
      )

def sphinxarg() -> argparse.ArgumentParser:
  return parsers.sphinxarg_common(
        sys.modules[__name__].__doc__,
        parser,
  )

def parser(subp: argparse.ArgumentParser) -> None:
  '''Register the `login` sub-parser'''
  pr = subp.add_parser('login',
                       help='Start an interactive session',
                       aliases=['init'])
  pr.set_defaults(recipe_cb=login, aksk = False)
  pr.add_argument('--aksk',
                  action = 'store_true',
                  help = 'Issue temporary AK/SK credentials')
  pr.add_argument('--token',
                  dest = 'aksk',
                  action = 'store_false',
                  help = 'Issue token (Default)')
  pr.add_argument('--ttl',
                  type = int,
                  default = 3600,
                  help = 'Credentials Time-to-live in seconds (only for temp AK/SK)')
  pr.add_argument('--s3cfg',
                  action  = 'store_true',
                  help = 'If issuing AK/SK, update ~/.s3cfg')
  pr.add_argument('--region','-R',
                  default = os.getenv('OS_TENANT_NAME',os.getenv('OS_REGION','eu-de')),
                  help = 'Unscoped token for the given region')

  pr = subp.add_parser('logout',
                       help='Discard cached session',
                     )
  pr.set_defaults(recipe_cb=logout)
  pr.add_argument('--s3cfg',
                  action  = 'store_true',
                  help = 'Update ~/.s3cfg')


parsers.register_parser('login', parser)
