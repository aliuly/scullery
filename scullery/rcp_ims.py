#
# IMS recipes
#
'''
Image management service

This recipe is used to list images

[API Docs](https://docs.otc.t-systems.com/image-management-service/api-ref/native_openstack_apis/image_native_openstack_apis/querying_images_native_openstack_api.html#en-us-topic-0060804959-table33420935171457)

'''

import argparse
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from . import clouds
from . import formatters
from . import parsers


# Columns for the list (default table) view.
COLUMNS: formatters.Columns = [
  ('name', 'Name'),
  ('id',   'ID'),
]

def list_ims(args: argparse.Namespace) -> None:
  '''List images, optionally filtered by key=value pairs'''
  params = dict()

  for kvp in args.param:
    if '=' not in kvp:
      raise SyntaxError(f'{kvp}: Must specify key=value pair')
    key, value = kvp.split('=',1)
    params[key] = value
  if args.type is not None:
    params['__os_type'] = args.type
  if args.os is not None:
    params['__platform'] = args.os

  cc = clouds.session(args, scoped = True)
  data = list(cc.ims.images(**params))
  rows = formatters.extract_rows(data, COLUMNS)
  formatters.write_output(rows, COLUMNS, args.format)

def get_ims(args: argparse.Namespace) -> None:
  '''Show detailed info for one or more images'''
  cc = clouds.session(args, scoped = True)
  for image in args.image:
    for found in cc.ims.images(name = image):
      formatters.write_single_output(found, args.format)

def sphinxarg() -> argparse.ArgumentParser:
  return parsers.sphinxarg_common(
        sys.modules[__name__].__doc__,
        parser,
  )


def parser(subp: argparse.ArgumentParser) -> None:
  '''Register the ``images`` sub-parser'''
  pr = subp.add_parser('image',
            help = 'Image management',
            aliases = ['ims', 'img'])
  # pr.set_defaults(recipe_cb = list_ims, param=[])
  pr.set_defaults(recipe_cb = lambda _: pr.print_help(), param=[])

  formatters.add_format_arg(pr)

  sp = pr.add_subparsers(title='op',
                          description='Operation.',
                          required = False,
                          help = 'Operation')

  pp = sp.add_parser('get',
                  help = 'Get details for image',
                )
  pp.add_argument('image',
                  help='Image to check',
                  nargs='+')
  pp.set_defaults(recipe_cb = get_ims)
  formatters.add_single_format_arg(pp)

  pp = sp.add_parser('list',
                  help = 'Find image',
                  aliases = ['find','ls'])
  pp.add_argument('--os',
                    help='Specify the image os platform',
                    choices = [
                        'Windows',
                        'Ubuntu',
                        'Red Hat',
                        'SUSE',
                        'CentOS',
                        'Debian',
                        'OpenSUSE',
                        'Oracle Linux',
                        'Fedora',
                        'CoreOS',
                        'EulerOS',
                        'Other',
                    ],
                    default = None,
                  )
  pp.add_argument('--type',
                    help='Specify an OS type',
                    choices = [
                      'Linux',
                      'Windows',
                      'Other',
                    ],
                    default=None,
                  )
  pp.add_argument('param',
                  nargs='*',
                  help = 'Key=value parameters to filter list')
  pp.set_defaults(recipe_cb = list_ims)

parsers.register_parser('images',parser)



