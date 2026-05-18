#
# Config Wizard recipes
#
'''
Configuration Wizard

Lets you interactive configure your `config.yaml` file for use with
**scullery**.

It may update `$HOME/.s3cfg` if requested.
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
import questionary

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from . import parsers
from . import s3cfg
from . import __meta__

def run(args: argparse.Namespace) -> None:
  '''Configuration wizard'''
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

  mode = questionary.select(
    'Are you using username+password or Permanent AK/SK credentials?',
    choices = [
      'username+password',
      'permanent AK/SK',
    ]).ask()
  if mode == 'username+password':
    if 'clouds' not in code: code['clouds'] = dict()
    if __meta__.name not in code['clouds']: code['clouds'][__meta__.name] = dict()
    if 'ak' in code['clouds'][__meta__.name]:
      sys.stderr.write('Warning, "ak" key found.  It will override "auth" unless removed.\n')
    if 'auth' not in code['clouds'][__meta__.name]:code['clouds'][__meta__.name]['auth'] = dict()

    answers = questionary.form(
      username = questionary.text('Username: ',
          default = (
            code['clouds'][__meta__.name]['auth']['username'] if (
              'username' in code['clouds'][__meta__.name]['auth']
            ) else
              os.getenv('OS_USERNAME', os.getenv('USER', os.getenv('LOGNAME','')))
            ),
      ),
      password = questionary.password('Password: ',
          default = (
            code['clouds'][__meta__.name]['auth']['password'] if (
              'password' in code['clouds'][__meta__.name]['auth']
            ) else
              os.getenv('OS_PASSWORD','')
            ),
      ),
      domain = questionary.text('Domain (OTC000xxxx): ',
          default = (
            code['clouds'][__meta__.name]['auth']['user_domain_name'] if (
              'user_domain_name' in code['clouds'][__meta__.name]['auth']
            ) else
              os.getenv('OS_USER_DOMAIN_NAME','')
            ),
      ),
    ).ask()
    if not answers: sys.exit()
    if not (answers['username'] or answers['password'] or answers['domain']):
      sys.stderr.write('No credentials entered\n')
      sys.exit(0)

    if answers['username']:
      code['clouds'][__meta__.name]['auth']['username'] = answers['username']
    if answers['password']:
      code['clouds'][__meta__.name]['auth']['password'] = answers['password']
    if answers['domain']:
      code['clouds'][__meta__.name]['auth']['user_domain_name'] = answers['domain']
    s3 = False

  elif mode == 'permanent AK/SK':
    if 'clouds' not in code: code['clouds'] = dict()
    if __meta__.name not in code['clouds']: code['clouds'][__meta__.name] = dict()
    if 'auth' in code['clouds'][__meta__.name]:
      sys.stderr.write('Warning, "auth" section found.  Will be ignored\n')

    answers = questionary.form(
        ak = questionary.text('Access Key: ',
            default = (
              code['clouds'][__meta__.name]['ak'] if (
                'ak' in code['clouds'][__meta__.name]
              ) else
                os.getenv('OS_ACCESS_KEY','')
              ),
        ),
        sk = questionary.text('Secret Key: ',
            default = (
              code['clouds'][__meta__.name]['sk'] if (
                'sk' in code['clouds'][__meta__.name]
              ) else
                os.getenv('OS_SECRET_KEY','')
              ),
        ),
        s3cfg = questionary.confirm('Do you want modify/configure ~/.s3cfg? ',
              default = False,
            )
    ).ask()
    if not answers: sys.exit()
    if not (answers['ak'] and answers['sk']):
      sys.stderr.write('No credentials entered\n')
      sys.exit(0)

    code['clouds'][__meta__.name]['ak'] = answers['ak']
    code['clouds'][__meta__.name]['sk'] = answers['sk']
    s3 = answers['s3cfg']
  else:
    raise ValueError(mode)

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

    if s3:
      # Update ~/.s3cfg
      s3cfg.update(
          code['clouds'][__meta__.name]['ak'],
          code['clouds'][__meta__.name]['sk'],
      )

def sphinxarg() -> argparse.ArgumentParser:
  return parsers.sphinxarg_common(
        sys.modules[__name__].__doc__,
        parser,
  )

def parser(subp: argparse.ArgumentParser) -> None:
  '''Register the `configuration wizard` sub-parser'''
  pr = subp.add_parser('config-wizard',
                       help='Configure your client',
                       aliases=['wiz'])
  pr.set_defaults(recipe_cb=run)


parsers.register_parser('wiz', parser)
