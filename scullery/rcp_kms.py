#
# KMS recipes
#
'''
KMS (Key Management Service) recipes

Manage Customer Master Keys: list, create, delete, enable/disable,
and rotate keys.

| Recipe | Description |
|--------|-------------|
|   | list all CMKs |
| ls | same as above |
| ls --state enabled | list keys filtered by state |
| ls --all | list keys in *all* states (including pending) |
| get id-or-alias | show key details and rotation status |
| create alias [--desc "..."] [--origin kms or external] | create a new CMK |
| delete id-or-alias [--pending-days N] | schedule key deletion (default 7 d) |
| cancel-delete id-or-alias | cancel a pending deletion |
| enable id-or-alias | enable a disabled key |
| disable id-or-alias | disable an enabled key |
| rotate id-or-alias [--period N] | enable auto-rotation; ``--period 0`` to disable |

Example YAML key states:

.. code-block:: yaml

   1: Pending creation
   2: Enabled
   3: Disabled
   4: Pending deletion
   5: Pending import

See :class:`scullery.kms.Kms` for API details.
'''

import argparse
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from . import clouds
from . import formatters
from . import kms
from . import parsers


# ── Column definitions ────────────────────────────────────────────────

COLUMNS: formatters.Columns = [
  ('key_id',                    'Key ID'),
  ('key_alias',                 'Alias'),
  ('key_state',                 'State'),
  ('key_spec',                  'Spec'),
  ('origin',                    'Origin'),
  ('creation_date',             'Created'),
  ('scheduled_deletion_date',   'Deletion Scheduled'),
  ('key_description',           'Description'),
]

COLUMNS_HUMAN: formatters.Columns = [
  ('key_alias',         'Alias'),
  ('key_state',         'State'),
  ('creation_date',     'Created'),
  ('key_description',   'Description'),
]

COLUMNS_HUMAN_FULL: formatters.Columns = [
  ('key_id',                    'Key ID'),
  ('key_alias',                 'Alias'),
  ('key_state',                 'State'),
  ('key_spec',                  'Spec'),
  ('origin',                    'Origin'),
  ('creation_date',             'Created'),
  ('scheduled_deletion_date',   'Deletion Scheduled'),
  ('key_description',           'Description'),
]


# ── Helpers ────────────────────────────────────────────────────────────

def _resolve(cc, name: str) -> str:
  '''Resolve *name* (alias or ID) to a canonical key ID, exiting on error.'''
  try:
    return cc.kms.resolve_key(name)
  except KeyError as e:
    sys.stderr.write(f'[error] {e}\n')
    sys.exit(1)


def _map_states(data: list[dict], *, human: bool = False) -> list[dict]:
  '''Replace numeric key_state with human-readable labels.

  When *human* is True the original numeric value is preserved in
  ``_key_state_code`` so the ``State`` column can be filtered later.
  '''
  for r in data:
    code = r.get('key_state', '')
    if isinstance(code, int):
      label = kms.STATE_NAMES.get(code, str(code))
      if human:
        r['_key_state_code'] = code
        r['key_state'] = label
      else:
        r['key_state'] = label
    r.setdefault('key_alias', '')
    r.setdefault('key_description', '')
    r.setdefault('scheduled_deletion_date', '')
    r.setdefault('key_spec', '')
    r.setdefault('origin', '')
    r.setdefault('creation_date', '')
  return data


def _parse_state(name: str) -> int:
  '''Parse a state name or number, returning the numeric code.

  Accepts names like ``"enabled"``, ``"pending deletion"``,
  ``"pending-deletion"``, or bare numbers ``"2"``.
  '''
  n = name.strip()
  # numeric
  if n.isdigit():
    v = int(n)
    if v in kms.STATE_NAMES:
      return v
    raise ValueError(f'Unknown state code: {n}')

  # canonical name
  lower = n.lower()
  if lower in kms.STATE_BY_NAME:
    return kms.STATE_BY_NAME[lower]

  # allow dashed aliases
  dashed = lower.replace('-', ' ')
  if dashed in kms.STATE_BY_NAME:
    return kms.STATE_BY_NAME[dashed]

  raise ValueError(f'Unknown state: "{name}".  '
                   f'Valid: {", ".join(kms.STATE_NAMES.values())} '
                   f'or numbers {", ".join(str(x) for x in kms.STATE_NAMES)}')


# ── List ───────────────────────────────────────────────────────────────

def list_keys(args: argparse.Namespace) -> None:
  '''List CMKs, optionally filtered by state.'''
  cc = clouds.session(args, scoped=True)

  state_filter: int | None = None
  if args.state is not None:
    state_filter = _parse_state(args.state)
  elif not args.all:
    # Default: active keys only (Enabled + Disabled).
    # The v2 API only accepts a single state value, so we fetch both
    # and merge when no explicit state is given.
    pass

  if state_filter is not None:
    data = cc.kms.keys(key_state=state_filter)
  elif not args.all:
    # merge enabled + disabled
    d1 = cc.kms.keys(key_state=kms.STATE_ENABLED)
    d2 = cc.kms.keys(key_state=kms.STATE_DISABLED)
    # Dedup by key_id (they shouldn't overlap, but be safe).
    seen = set()
    data = []
    for r in d1 + d2:
      if r['key_id'] not in seen:
        seen.add(r['key_id'])
        data.append(r)
  else:
    data = cc.kms.keys()

  human = args.format in ('terminal', 'markdown')
  data = _map_states(data, human=human)

  if human:
    cols = COLUMNS_HUMAN_FULL if getattr(args, 'long', False) else COLUMNS_HUMAN
  else:
    cols = COLUMNS

  rows = formatters.extract_rows(data, cols)
  formatters.write_output(rows, cols, args.format)


# ── Get ────────────────────────────────────────────────────────────────

def get_key(args: argparse.Namespace) -> None:
  '''Show detailed information for one or more keys.'''
  cc = clouds.session(args, scoped=True)
  for name in args.name:
    key_id = _resolve(cc, name)
    info = cc.kms.describe(key_id)
    code = info.get('key_state', '')
    if isinstance(code, int):
      info['key_state'] = kms.STATE_NAMES.get(code, str(code))
    formatters.write_single_output(info, args.format)


# ── Create ─────────────────────────────────────────────────────────────

def create_key(args: argparse.Namespace) -> None:
  '''Create a new CMK.'''
  if args.alias.endswith('/default'):
    sys.stderr.write('[error] Key aliases ending in "/default" are not allowed\n')
    sys.exit(1)
  cc = clouds.session(args, scoped=True)
  xopts = {}
  if args.key_usage is not None: xopts['key_usage'] = args.key_sage
  info = cc.kms.create(
      alias=args.alias,
      description=args.description,
      key_spec=args.key_spec,
      **xopts,
  )
  sys.stderr.write(f'Created key "{args.alias}" ({info["key_id"]})\n')
  formatters.write_single_output(info, args.format)


# ── Delete / cancel-delete ─────────────────────────────────────────────

def delete_key(args: argparse.Namespace) -> None:
  '''Schedule one or more keys for deletion.'''
  cc = clouds.session(args, scoped=True)
  for name in args.name:
    key_id = _resolve(cc, name)
    info = cc.kms.schedule_deletion(key_id, pending_days=args.pending_days)
    sys.stderr.write(f'Scheduled deletion of "{name}"\n')


def cancel_delete(args: argparse.Namespace) -> None:
  '''Cancel scheduled deletion for one or more keys.'''
  cc = clouds.session(args, scoped=True)
  for name in args.name:
    key_id = _resolve(cc, name)
    cc.kms.cancel_deletion(key_id)
    sys.stderr.write(f'Cancelled deletion of "{name}"\n')


# ── Enable / disable ───────────────────────────────────────────────────

def enable_key(args: argparse.Namespace) -> None:
  '''Enable one or more disabled keys.'''
  cc = clouds.session(args, scoped=True)
  for name in args.name:
    key_id = _resolve(cc, name)
    cc.kms.enable(key_id)
    sys.stderr.write(f'Enabled "{name}"\n')


def disable_key(args: argparse.Namespace) -> None:
  '''Disable one or more enabled keys.'''
  cc = clouds.session(args, scoped=True)
  for name in args.name:
    key_id = _resolve(cc, name)
    cc.kms.disable(key_id)
    sys.stderr.write(f'Disabled "{name}"\n')


# ── Rotate ─────────────────────────────────────────────────────────────

def rotate_key(args: argparse.Namespace) -> None:
  '''Enable, disable, or show automatic key rotation status.'''
  cc = clouds.session(args, scoped=True)
  period = getattr(args, 'period', None)
  for name in args.name:
    key_id = _resolve(cc, name)
    status = cc.kms.rotate(key_id, period=period)
    if period is None:
      enabled = 'enabled' if status['key_rotation_enabled'] else 'disabled'
      interval = status.get('rotation_interval', 0)
      line = f'"{name}": rotation {enabled}'
      if interval:
        line += f', interval={interval} d'
      print(line)
    elif period > 0:
      sys.stderr.write(f'Rotation enabled on "{name}" (period={period} d)\n')
    else:
      sys.stderr.write(f'Rotation disabled on "{name}"\n')




# ── Parser ─────────────────────────────────────────────────────────────

def sphinxarg() -> argparse.ArgumentParser:
  return parsers.sphinxarg_common(
        sys.modules[__name__].__doc__,
        parser,
  )

def parser(subp: argparse.ArgumentParser) -> None:
  '''Register the ``kms`` sub-parser.'''
  pr = subp.add_parser('kms',
                        help='Key Management Service recipes',
                      )
  pr.set_defaults(recipe_cb=list_keys, state= None, all = False)
  formatters.add_format_arg(pr)
  pr.add_argument('--long', '-l',
                  action='store_true', default=False,
                  help='Show key ID column in human-readable output')

  sp = pr.add_subparsers(title='op',
                          description='Operation.  If not specified, list keys.',
                          required=False,
                          help='Operation')

  # -- ls ----------------------------------------------------------------
  pp = sp.add_parser('ls',
                      help='List CMKs',
                      aliases=['list'])
  pp.add_argument('--state', '-s',
                  default=None,
                  help='Filter by key state (name or number)')
  pp.add_argument('--all', '-a',
                  action='store_true', default=False,
                  help='List keys in all states (default: Enabled + Disabled)')
  pp.set_defaults(recipe_cb=list_keys)
  formatters.add_format_arg(pp)
  pp.add_argument('--long', '-l',
                  action='store_true', default=False,
                  help='Show key-ID column in human-readable output')

  # -- get ---------------------------------------------------------------
  pp = sp.add_parser('get',
                      help='Show key details',
                      aliases=['show', 'info', 'describe'])
  pp.add_argument('name',
                  nargs='+',
                  help='Key alias or ID')
  pp.set_defaults(recipe_cb=get_key)
  formatters.add_single_format_arg(pp)

  # -- create ------------------------------------------------------------
  pp = sp.add_parser('create',
                      help='Create a new CMK',
                      aliases=['mk', 'new', 'add'])
  pp.add_argument('alias',
                  help='Key alias (display name)')
  pp.add_argument('--desc', '--description',
                  dest='description', default=None,
                  help='Key description')
  pp.add_argument('--key-spec', '--key_spec', '-k',
                  dest='key_spec',
                  choices=['AES_256', 'RSA_2048',
                            'RSA_3072', 'RSA_4096',
                            'EC_P256', 'EC_P348',
                            'HMAC_256', 'HMAC_384', 'HMAC_512' ],
                  default='AES_256',
                  help='Key spec (default: AES_256)')
  pp.add_argument('--key-usage', '--key_usage', '-u',
                  dest='key_usage',
                  choices=['ENCRYPT_DECRYPT', 'SIGN_VERIFY'],
                  default=None,
                  help='Key usage (default: depends on key type)')
  pp.set_defaults(recipe_cb=create_key)
  formatters.add_single_format_arg(pp)

  # -- delete ------------------------------------------------------------
  pp = sp.add_parser('delete',
                      help='Schedule key deletion',
                      aliases=['del', 'rm', 'remove'])
  pp.add_argument('name',
                  nargs='+',
                  help='Key alias or ID to delete')
  pp.add_argument('--pending-days', '--pending_days', '-d',
                  dest='pending_days',
                  type=int, default=7,
                  help='Days before permanent deletion (default: 7)')
  pp.set_defaults(recipe_cb=delete_key)

  # -- cancel-delete -----------------------------------------------------
  pp = sp.add_parser('cancel-delete',
                      help='Cancel a scheduled key deletion',
                      aliases=['cancel', 'undelete', 'undel'])
  pp.add_argument('name',
                  nargs='+',
                  help='Key alias or ID to restore')
  pp.set_defaults(recipe_cb=cancel_delete)

  # -- enable ------------------------------------------------------------
  pp = sp.add_parser('enable',
                      help='Enable a disabled key',
                      aliases=['on'])
  pp.add_argument('name',
                  nargs='+',
                  help='Key alias or ID to enable')
  pp.set_defaults(recipe_cb=enable_key)

  # -- disable -----------------------------------------------------------
  pp = sp.add_parser('disable',
                      help='Disable an enabled key',
                      aliases=['off'])
  pp.add_argument('name',
                  nargs='+',
                  help='Key alias or ID to disable')
  pp.set_defaults(recipe_cb=disable_key)

  # -- rotate ------------------------------------------------------------
  pp = sp.add_parser('rotate',
                      help='Enable, disable, or show key rotation status',
                      aliases=['rotation'])
  pp.add_argument('name',
                  nargs='+',
                  help='Key alias or ID')
  pp.add_argument('--period', '-p',
                  type=int, default=None,
                  help='Rotation interval in days (30–365). '
                       'Use 0 to disable.  '
                       'Omit to show current status.')
  pp.set_defaults(recipe_cb=rotate_key)



parsers.register_parser('kms', parser)
