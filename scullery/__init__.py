#!/usr/bin/env python3
''' Recipe runner

'''

import os
import sys

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

import creds
import api

sys.path = saved_path
del saved_path

clouds = {}
'''Dictionary keeping cloud connections'''

defaults = {
  'cloud': None,
}

#
# Support functions
#
def cloud(cloud_name:str = '', **kwargs) -> api.ApiSession:
  '''Return connections to clouds'''

  if not cloud_name in clouds:
    fopts = dict(kwargs)
    if cloud_name != '':
      fopts['cloud_name'] = cloud_name
    else:
      fopts['cloud_name'] = defaults['cloud'] # Default cloud
    cloud_creds = creds.creds(**fopts)

    clouds[cloud_name] = api.ApiSession(cloud_creds)

  return clouds[cloud_name]

def clean_up()->None:
  keys = list(clouds.keys())
  for k in keys:
    del clouds[k]
