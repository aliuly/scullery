#
# Object recipes
#
'''
OBS Object recipes

List, upload, download, and delete objects in OBS/S3 buckets.

Credentials are acquired via :func:`~scullery.clouds.s3session`.

| Recipe | Description |
|--------|-------------|
| ls ``bucket`` [``prefix``] | list objects in a bucket |
| put ``bucket`` ``key`` ``file`` | upload a local file |
| get ``bucket`` ``key`` [``outfile``] | download an object |
| rm ``bucket`` ``key`` | delete an object |
| info ``bucket`` ``key`` | show object metadata |

This is a basic implementation, just enough to support bootstrapping.
It has the following limitations:

* Max 1,000 objects per bucket
* Can only upload/download objects that can fit in memory.
* No support for resumable uploads/downloads.
'''

import argparse
import os
import sys

try:
    from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
    ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from . import clouds
from . import formatters
from . import parsers

# ── Column definitions ───────────────────────────────────────────────

COLUMNS: formatters.Columns = [
    ('key',            'Key'),
    ('size',           'Size'),
    ('last_modified',  'Last Modified'),
    ('storage_class',  'Storage Class'),
    ('ETag',           'ETag'),
]

COLUMNS_HUMAN: formatters.Columns = [
    ('key',            'Key'),
    ('size',           'Size'),
    ('last_modified',  'Last Modified'),
]

# ── Helpers ───────────────────────────────────────────────────────────

def _fmt_size(size: int) -> str:
    '''Format a byte size in human-readable form.'''
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'):
        if abs(size) < 1024.0:
            return f'{size:3.1f} {unit}'
        size /= 1024.0
    return f'{size:.1f} EiB'

# ── List ──────────────────────────────────────────────────────────────

def list_objects(args: argparse.Namespace) -> None:
  '''List objects in an OBS bucket, optionally filtered by prefix.'''
  cc = clouds.s3session(args)
  bucket = cc.bucket.objects(args.bucket)

  prefix = getattr(args, 'prefix', '') or None
  data = bucket.objects(prefix = prefix)
  # Format fields for display.
  for obj in data:
      if 'last_modified' in obj and obj['last_modified']:
          obj['last_modified'] = str(obj['last_modified'])[:19]
      if 'size' in obj:
          if args.format in ('terminal', 'markdown'):
              obj['size'] = _fmt_size(obj['size'])
          else:
              obj['size'] = int(obj['size'])
      if 'storage_class' not in obj or obj['storage_class'] is None:
          obj['storage_class'] = 'STANDARD'

  cols = COLUMNS_HUMAN if args.format in ('terminal', 'markdown') else COLUMNS
  rows = formatters.extract_rows(data, cols)
  formatters.write_output(rows, cols, args.format)

# ── Upload / Put ──────────────────────────────────────────────────────

def upload_object(args: argparse.Namespace) -> None:
  '''Upload a local file to an OBS bucket.'''
  local_path = args.file
  if not os.path.isfile(local_path):
    sys.stderr.write(f'[error] File not found: {local_path}\n')
    sys.exit(1)

  with open(local_path, 'rb') as fp:
    content = fp.read()

  cc = clouds.s3session(args)
  bucket = cc.bucket.objects(args.bucket)
  hdrs = dict()
  if args.content_type is not None:
    hdrs['Content-type'] = args.content_type

  bucket.put(args.key, content, hdrs)


# ── Download / Get ────────────────────────────────────────────────────

def download_object(args: argparse.Namespace) -> None:
  '''Download an object from an OBS bucket.'''

  cc = clouds.s3session(args)
  bucket = cc.bucket.objects(args.bucket)
  content = bucket.get(args.key)

  if args.output:
    with open(args.output, 'wb') as f:
      f.write(content)
    sys.stderr.write(f'Downloaded s3://{args.bucket}/{args.key} → "{args.output}"\n')
  else:
    # Write raw bytes to stdout.
    sys.stdout.buffer.write(content)
    sys.stderr.write(f'Downloaded s3://{args.bucket}/{args.key} - {len(content)} bytes\n"')

# ── Delete / Remove ───────────────────────────────────────────────────

def delete_object(args: argparse.Namespace) -> None:
  '''Delete an object from an OBS bucket.'''
  cc = clouds.s3session(args)
  bucket = cc.bucket.objects(args.bucket)
  content = bucket.delete(args.key)
  sys.stderr.write(f'Deleted s3://{args.bucket}/{args.key}\n')

# ── Head / Info ───────────────────────────────────────────────────────

def head_object(args: argparse.Namespace) -> None:
  '''Show metadata for an object (HEAD request).'''
  cc = clouds.s3session(args)
  bucket = cc.bucket.objects(args.bucket)
  hdr = bucket.meta(args.key)

  info = {
      'key':           args.key,
      'bucket':        args.bucket,
      'content_type':  hdr.get('Content-Type', ''),
      'content_length': int(hdr.get('Content-Length', 0)),
      'etag':          hdr.get('ETag', '').strip('"'),
      'last_modified': hdr.get('Last-Modified', ''),
  }

  def _terminal(obj: dict) -> str:
      return (
          f'Key:            {obj["key"]}\n'
          f'Bucket:         {obj["bucket"]}\n'
          f'Content-Type:   {obj["content_type"]}\n'
          f'Content-Length: {obj["content_length"]}\n'
          f'ETag:           {obj["etag"]}\n'
          f'Last-Modified:  {obj["last_modified"]}'
      )

  formatters.write_single_output(info, args.format, terminal_fn=_terminal)

# ── Parser ────────────────────────────────────────────────────────────

def sphinxarg() -> argparse.ArgumentParser:
    return parsers.sphinxarg_common(
        sys.modules[__name__].__doc__,
        parser,
    )

def parser(subp: argparse.ArgumentParser) -> None:
    '''Register the ``object`` sub-parser.'''
    pr = subp.add_parser('object',
                         help='Object Storage object operations',
                         aliases=['obj', 'obs'])
    # No default recipe_cb — a subcommand is always required.

    sp = pr.add_subparsers(title='op',
                           description='Operation.',
                           required=False,
                           help='Operation')

    # -- ls ----------------------------------------------------------------
    pp = sp.add_parser('ls',
                       help='List objects in a bucket',
                       aliases=['list'])
    pp.add_argument('bucket', help='Bucket name')
    pp.add_argument('prefix', nargs='?', default='',
                    help='Object key prefix filter')
    pp.set_defaults(recipe_cb=list_objects)
    formatters.add_format_arg(pp)

    # -- put ---------------------------------------------------------------
    pp = sp.add_parser('put',
                       help='Upload a file to a bucket',
                       aliases=['upload', 'up'])
    pp.add_argument('bucket', help='Bucket name')
    pp.add_argument('key', help='Object key (path in the bucket)')
    pp.add_argument('file', help='Local file to upload')
    pp.add_argument('--content-type', '-t',
                    dest='content_type', default=None,
                    help='Content-Type (auto-detected if omitted)')
    # ~ pp.add_argument('--public', '-p',
                    # ~ action='store_true', default=False,
                    # ~ help='Make the object publicly readable')
    pp.set_defaults(recipe_cb=upload_object)

    # -- get ---------------------------------------------------------------
    pp = sp.add_parser('get',
                       help='Download an object from a bucket',
                       aliases=['download', 'dl', 'cat'])
    pp.add_argument('bucket', help='Bucket name')
    pp.add_argument('key', help='Object key')
    pp.add_argument('output', nargs='?', default=None,
                    help='Output file (stdout if omitted)')
    pp.set_defaults(recipe_cb=download_object)

    # -- delete ------------------------------------------------------------
    pp = sp.add_parser('delete',
                       help='Delete an object from a bucket',
                       aliases=['del', 'rm', 'remove'])
    pp.add_argument('bucket', help='Bucket name')
    pp.add_argument('key', help='Object key')
    pp.set_defaults(recipe_cb=delete_object)

    # -- info --------------------------------------------------------------
    pp = sp.add_parser('info',
                       help='Show object metadata',
                       aliases=['head', 'stat', 'show'])
    pp.add_argument('bucket', help='Bucket name')
    pp.add_argument('key', help='Object key')
    pp.set_defaults(recipe_cb=head_object)
    formatters.add_single_format_arg(pp)


parsers.register_parser('object', parser)
