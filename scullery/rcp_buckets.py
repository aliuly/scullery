#
# Bucket / OBS recipes
#
'''
Object Storage Bucket recipes

List, create, delete, manage tags and access policies for OBS buckets.

| Recipe | Description |
|--------|-------------|
| | list all buckets (with tags) |
| ls | same as above |
| ls env=prod  | list buckets filtered by tag |
| ls env=prod --tag env  | filtered, showing tag column |
| create <name> |   create a new bucket |
| delete <name> | delete a bucket |
| tag <name>  |list bucket tags |
| tag <name> key=value ... | set (replace) tags |
| untag <name> key ... | delete tags by key |
| untag --all <name> | delete all tags |
| access <name> | show access policy |
| access <name> grant <who> <perm> | grant access (IAM user/group) |
| access <name> revoke <who> <perm> | revoke access (IAM user/group) |

Access is managed via bucket policies.  Only IAM **users** are supported
as policy principals — IAM groups are **not** supported by the OBS/S3 API.

This recipe automatically acquires temporary AK/SK credentials if
the session uses password or token authentication.

'''

import argparse
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from . import clouds
from . import formatters
from . import obs
from . import parsers


# ── Column definitions ─────────────────────────────────────────────

COLUMNS_BUCKETS: formatters.Columns = [
    ('name',          'Name'),
    ('creation_date', 'Created'),
]


# ── Commands ───────────────────────────────────────────────────────

def _list_buckets(args: argparse.Namespace,
                  tag_filters: dict[str, str] | None = None) -> None:
    '''List OBS buckets, optionally filtered by tag KEY=VALUE pairs.

    :param args:        Parsed arguments (uses *format*, *list_tags*).
    :param tag_filters: Optional dict of ``{key: value}`` to filter by.
    '''
    cc = clouds.s3session(args)
    data = cc.bucket.buckets()

    # Format creation_date to just the date part.
    for bucket in data:
        if 'creation_date' in bucket and bucket['creation_date']:
            bucket['creation_date'] = bucket['creation_date'][:10]

    cols = list(COLUMNS_BUCKETS)

    # Always fetch tags for every bucket.
    for bucket in data:
        try:
            tags = cc.bucket.get_tagging(bucket['name'])
            bucket['tags'] = {t['key']: t['value'] for t in tags}
        except Exception:
            bucket['tags'] = {}

    # Apply tag filters if given.
    if tag_filters:
        filtered = []
        for bucket in data:
            tag_map = bucket.get('tags', {})
            if all(tag_map.get(k) == v for k, v in tag_filters.items()):
                filtered.append(bucket)
        data = filtered

    list_tags = getattr(args, 'list_tags', None)

    if list_tags:
        # Specific tag keys requested — show individual columns.
        for tag_key in list_tags:
            cols.append((f'tag:{tag_key}', f'Tag:{tag_key}'))
        for bucket in data:
            tag_map = bucket.pop('tags', {})
            for tag_key in list_tags:
                bucket[f'tag:{tag_key}'] = tag_map.get(tag_key, '')
    else:
        # Combined "Tags" column.
        # Keep as a dict for structured formats; flatten for tabular/human ones.
        if args.format not in ('json', 'yaml'):
            for bucket in data:
                tag_map = bucket.pop('tags', {})
                bucket['tags'] = ', '.join(
                    f'{k}={v}' for k, v in sorted(tag_map.items())
                )
        cols.append(('tags', 'Tags'))

    rows = formatters.extract_rows(data, cols)
    formatters.write_output(rows, cols, args.format)

def list_buckets(args: argparse.Namespace) -> None:
    '''List all OBS buckets (no filtering)'''
    _list_buckets(args)


def list_buckets_filtered(args: argparse.Namespace) -> None:
    '''List OBS buckets filtered by tag KEY=VALUE pairs.'''
    tag_filters: dict[str, str] = {}
    for f in args.filter:
        if '=' not in f:
            sys.stderr.write(f'[error] Invalid filter "{f}": expected KEY=VALUE\n')
            sys.exit(1)
        k, v = f.split('=', 1)
        tag_filters[k.strip()] = v.strip()
    _list_buckets(args, tag_filters)


def create_bucket(args: argparse.Namespace) -> None:
    '''Create an OBS bucket'''
    cc = clouds.s3session(args)
    kms_key_id = None
    if args.kms_key:
        kms_key_id = _resolve_kms_key(args, args.kms_key)
    cc.bucket.create(args.name, location=args.location,
                     kms_key_id=kms_key_id)
    msg = f'Bucket "{args.name}" created.'
    if kms_key_id:
        msg += f' (SSE-KMS key: {kms_key_id})'
    print(msg)


def delete_bucket(args: argparse.Namespace) -> None:
    '''Delete an OBS bucket'''
    cc = clouds.s3session(args)
    cc.bucket.delete(args.name)
    print(f'Bucket "{args.name}" deleted.')


# ── KMS key resolution ────────────────────────────────────────────────

def _resolve_kms_key(args: argparse.Namespace, name_or_id: str) -> str:
    '''Resolve a KMS key alias or key ID to a canonical key ID.

    Fast path: if *name_or_id* looks like a UUID (contains ``-``
    and ≥ 32 chars), return it as-is without any API call.

    Slow path: create a scoped API session and resolve via the KMS
    ``resolve_key`` method (which does alias→ID lookup).

    :param args:        Parsed command-line arguments.
    :param name_or_id:  KMS key alias or key ID.
    :returns:           Canonical key ID (UUID string).
    :raises SystemExit: If the key cannot be resolved.
    '''
    # Fast path: input already looks like a UUID.
    if '-' in name_or_id and len(name_or_id) >= 32:
        return name_or_id

    # Slow path: resolve alias via KMS API.
    cc = clouds.session(args, scoped=True)
    try:
        return cc.kms.resolve_key(name_or_id)
    except KeyError as e:
        sys.stderr.write(f'[error] {e}\n')
        sys.exit(1)


# ── Tag helpers ─────────────────────────────────────────────────────

def _parse_kvp(kvp: str) -> tuple[str, str]:
    '''Split a ``key=value`` string into ``(key, value)``.

    If no ``=`` is present, both key and value are set to the same string.
    '''
    if '=' in kvp:
        k, v = kvp.split('=', 1)
    else:
        k = v = kvp
    return k.strip(), v.strip()


# ── Tag commands ───────────────────────────────────────────────────

def show_tags(args: argparse.Namespace) -> None:
    '''Show or set tags on a bucket.

    When *args.tag* is provided (one or more ``key=value`` pairs), the
    tags are replaced.  Otherwise the current tags are displayed.
    '''
    cc = clouds.s3session(args)

    # If key=value pairs given, switch to set mode.
    if args.tag:
        tags = {}
        for d in cc.bucket.get_tagging(args.name):
          tags[d['key']] = d['value']
        tags.update([_parse_kvp(kvp) for kvp in args.tag])
        tag_dicts = [{'key': k, 'value': v} for k, v in tags.items()]
        cc.bucket.set_tagging(args.name, tag_dicts)
        print(f'Tags set on bucket "{args.name}".')
        return

    # Otherwise display current tags.
    tags = cc.bucket.get_tagging(args.name)

    if args.format == 'terminal':
        if not tags:
            print(f'No tags on bucket "{args.name}".')
            return
        for t in tags:
            print(f'{t["key"]}={t["value"]}')
    else:
        formatters.write_single_output({'tags': tags}, args.format)


def delete_tags(args: argparse.Namespace) -> None:
    '''Delete tags from a bucket'''
    cc = clouds.s3session(args)

    if args.all:
        cc.bucket.delete_tagging(args.name)
        print(f'All tags removed from bucket "{args.name}".')
        return

    # Read current tags, remove matching keys, write back.
    current = cc.bucket.get_tagging(args.name)
    if len(current) == 0:
      print('Nothing to do')
      return
    keys_to_remove = set(args.key)
    remaining = [t for t in current if t['key'] not in keys_to_remove]

    if len(remaining) == len(current):
        print(f'None of the specified keys found on bucket "{args.name}".')
        return
    elif len(remaining) == 0:
        cc.bucket.delete_tagging(args.name)
        print(f'All tags removed from bucket "{args.name}".')
        return

    # ~ ic(remaining)
    cc.bucket.set_tagging(args.name, remaining)
    removed = len(current) - len(remaining)
    print(f'Removed {removed} tag(s) from bucket "{args.name}".')


# ── Access commands ────────────────────────────────────────────────

def _resolve_principal(args: argparse.Namespace, who: str) -> tuple[str, str]:
    '''Resolve an IAM user name to a principal type and S3-compatible URN.

    Looks up the IAM user by name, retrieves the domain (account) ID,
    and builds a principal ARN suitable for use in a bucket policy.

    :param args: Parsed command-line arguments (used to create an IAM session).
    :param who:  IAM user name to resolve.
    :returns:    Tuple of ``(principal_type, principal_urn)``.
    :raises SystemExit: If the user cannot be found or the domain is unclear.
    '''
    api = clouds.session(args)
    users = api.iam.users(who)
    if len(users) != 1:
        sys.stderr.write(f'[error] IAM user "{who}" not found.\n')
        sys.exit(1)

    domain_id = users[0].get('domain_id')
    if not domain_id:
        sys.stderr.write(f'[error] Cannot determine domain ID for user "{who}".\n')
        sys.exit(1)

    principal_type = 'user'
    principal_urn = obs.Buckets._principal_urn(domain_id, principal_type, who)
    return principal_type, principal_urn


def show_access(args: argparse.Namespace) -> None:
    '''Display the bucket access policy, or dispatch grant/revoke.'''
    if args.op == 'grant':
        grant_access(args)
        return
    if args.op == 'revoke':
        revoke_access(args)
        return

    # Show the current policy.
    cc = clouds.s3session(args)
    policy = cc.bucket.get_policy(args.name)

    if args.format == 'terminal':
        stmts = policy.get('Statement', [])
        if not stmts:
            print(f'No bucket policy on "{args.name}".')
            return
        for s in stmts:
            principals = s.get('Principal', {}).get('AWS', [])
            if isinstance(principals, str):
                principals = [principals]
            actions = s.get('Action', [])
            if isinstance(actions, str):
                actions = [actions]
            effect = s.get('Effect', '?')
            for p in principals:
                # Shorten URN to just the name part.
                short = p.rsplit(':', 1)[-1] if ':' in p else p
                print(f'  {effect:5s}  {short:30s}  {", ".join(actions)}')
    else:
        formatters.write_single_output(policy, args.format)


def grant_access(args: argparse.Namespace) -> None:
    '''Grant bucket access to an IAM user (groups not supported)'''
    if not args.who or not args.permission:
        sys.stderr.write('[error] Usage: access <name> grant <who> <perm>\n')
        sys.exit(1)
    cc = clouds.s3session(args)
    ptype, principal_urn = _resolve_principal(args, args.who)
    cc.bucket.grant_policy(args.name, principal_urn, args.permission.upper())
    print(f'Granted "{args.permission.upper()}" on "{args.name}" to {ptype} "{args.who}".')


def revoke_access(args: argparse.Namespace) -> None:
    '''Revoke bucket access from an IAM user (groups not supported)'''
    if not args.who or not args.permission:
        sys.stderr.write('[error] Usage: access <name> revoke <who> <perm>\n')
        sys.exit(1)
    cc = clouds.s3session(args)
    ptype, principal_urn = _resolve_principal(args, args.who)
    cc.bucket.revoke_policy(args.name, principal_urn, args.permission.upper())
    print(f'Revoked "{args.permission.upper()}" on "{args.name}" from {ptype} "{args.who}".')


# ── Encryption commands ──────────────────────────────────────────────

def handle_encryption(args: argparse.Namespace) -> None:
    '''Manage default encryption on a bucket (SSE-KMS or SSE-S3).'''
    cc = clouds.s3session(args)

    if args.off:
        cc.bucket.delete_encryption(args.name)
        print(f'Default encryption removed from bucket "{args.name}".')
    elif args.kms_key:
        key_id = _resolve_kms_key(args, args.kms_key)
        cc.bucket.set_encryption(args.name, 'aws:kms', kms_key_id=key_id)
        print(f'SSE-KMS enabled on bucket "{args.name}" (key: {key_id}).')
    elif args.sse_s3:
        cc.bucket.set_encryption(args.name, 'AES256')
        print(f'SSE-S3 (AES256) enabled on bucket "{args.name}".')
    else:
        cfg = cc.bucket.get_encryption(args.name)
        if cfg is None:
            print(f'No default encryption configured on bucket "{args.name}".')
        else:
            formatters.write_single_output(cfg, args.format)


# ── Parser ─────────────────────────────────────────────────────────

def sphinxarg() -> argparse.ArgumentParser:
  return parsers.sphinxarg_common(
        sys.modules[__name__].__doc__,
        parser,
  )

def parser(subp: argparse.ArgumentParser) -> None:
    '''Register the ``bucket`` sub-parser'''
    pr = subp.add_parser('bucket',
                         help='Object Storage Bucket management',
                       )
    pr.set_defaults(recipe_cb=list_buckets)
    formatters.add_format_arg(pr)

    sp = pr.add_subparsers(title='op',
                           description='Operation.  If not specified, list buckets.',
                           required=False,
                           help='Operation')

    # -- create ----------------------------------------------------------
    pp = sp.add_parser('create',
                       help='Create a new bucket',
                       aliases=['mk', 'new'])
    pp.add_argument('name', help='Bucket name (globally unique)')
    pp.add_argument('--location', '-l', default=None,
                    help='Bucket location (region). Defaults to session region.')
    pp.add_argument('--kms-key', '-k',
                    dest='kms_key', default=None,
                    help='KMS key alias or ID (UUID) for SSE-KMS default encryption')
    pp.set_defaults(recipe_cb=create_bucket)

    # -- delete ----------------------------------------------------------
    pp = sp.add_parser('delete',
                       help='Delete a bucket (must be empty)',
                       aliases=['del', 'rm', 'remove'])
    pp.add_argument('name', help='Bucket name')
    pp.set_defaults(recipe_cb=delete_bucket)

    # -- ls ----------------------------------------------------------------
    pp = sp.add_parser('ls',
                       help='List buckets, optionally filtered by tag',
                       aliases=['list', 'filter'])
    pp.add_argument('filter',
                    nargs='*',
                    help='Tag filter as KEY=VALUE (repeatable)')
    pp.add_argument('--tag',
                    action='append',
                    default=[],
                    dest='list_tags',
                    metavar='KEY',
                    help='Display specific tag KEY as a column (repeatable; '
                         'default: all tags in a combined column)')
    pp.set_defaults(recipe_cb=list_buckets_filtered)
    formatters.add_format_arg(pp)

    # -- tag -------------------------------------------------------------
    pp = sp.add_parser('tag',
                       help='Show or set tags on a bucket',
                     )
    pp.add_argument('name', help='Bucket name')
    pp.add_argument('tag',
                    nargs='*',
                    help='Tag as key=value (if omitted, list existing tags)')
    pp.set_defaults(recipe_cb=show_tags)
    formatters.add_single_format_arg(pp)

    # -- untag -----------------------------------------------------------
    pp = sp.add_parser('untag',
                       help='Delete tags from a bucket',
                       aliases=['tag-del', 'rmtag'])
    pp.add_argument('name', help='Bucket name')
    pp.add_argument('key',
                    nargs='*',
                    help='Tag key(s) to remove')
    pp.add_argument('--all', '-a',
                    action='store_true',
                    default=False,
                    help='Delete all tags from the bucket')
    pp.set_defaults(recipe_cb=delete_tags)

    # -- access ----------------------------------------------------------
    pp = sp.add_parser("access",
                       help="Manage bucket access policy (IAM users",
                       aliases=["policy",'pol'])
    pp.add_argument("name", help="Bucket name")
    pp.add_argument("op", nargs="?",
                    choices=["grant", "revoke"],
                    help="Operation (grant or revoke)")
    pp.add_argument("who", nargs="?",
                    help="IAM user name")
    pp.add_argument("permission", nargs="?",
                    choices=["READ", "WRITE", "FULL_CONTROL"],
                    help="Permission to grant/revoke")
    pp.set_defaults(recipe_cb=show_access)
    formatters.add_single_format_arg(pp)

    # -- encryption -------------------------------------------------------
    pp = sp.add_parser('encryption',
                       help='Manage bucket default encryption (SSE-KMS / SSE-S3)',
                       aliases=['enc', 'sse'])
    pp.add_argument('name', help='Bucket name')
    xgrp = pp.add_mutually_exclusive_group()
    xgrp.add_argument('--kms-key', '-k',
                      dest='kms_key', default=None,
                      help='Enable SSE-KMS with this key alias or ID (UUID)')
    xgrp.add_argument('--sse-s3', '-s',
                      dest='sse_s3', action='store_true', default=False,
                      help='Enable SSE-S3 (AES256)')
    xgrp.add_argument('--off', '-o',
                      dest='off', action='store_true', default=False,
                      help='Disable default encryption')
    pp.set_defaults(recipe_cb=handle_encryption)
    formatters.add_single_format_arg(pp)


parsers.register_parser('bucket', parser)
