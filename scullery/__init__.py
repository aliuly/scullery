#!/usr/bin/env python3
''' Recipe runner

'''

import os
import sys
# ~ import typing
# ~ import yaml

from distutils.util import strtobool

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa


saved_path = list(sys.path)
''' _private_
:meta private:
'''
sys.path.append(os.path.dirname(__file__))

from version import VERSION
import __meta__
import consts as K

sys.path = saved_path
del saved_path

import ypp

clouds = {}
'''Dictionary keeping cloud connections'''

#
# Support functions
#
def cloud(cloud_name:str = '', **kwargs):
  '''Return connections to clouds'''
  if len(clouds) == 0:
    opt = ypp.lookup(K.OPENSTACK_LOGGING)
    if not opt is None: openstack.enable_logging(strtobool(opt))

  if cloud_name is None: cloud_name = ''
  if not cloud_name in clouds:
    fopts = dict(kwargs)
    if cloud_name != '':
      fopts[K.CLOUD] = cloud_name
    else:
      opt = ypp.lookup(K.CLOUD)
      if not opt is None: fopts[K.CLOUD] = ypp.lookup(K.CLOUD)
    clouds[cloud_name] = openstack.connect(**fopts)

  return clouds[cloud_name]
