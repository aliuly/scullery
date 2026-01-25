#!python3
#
# IMS functionality
#
'''Implement Image Management services'''


try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

class Ims:
  '''Main class for IMS'''
  API_HOST = 'ims.{region}.otc.t-systems.com'
  '''API End-point'''

  def api_path(self, path) -> str:
    '''API URL path'''
    host = Ims.API_HOST.format(region = self.session.region)
    return f'https://{host}/{path}'

  def __init__(self, session) -> None:
    '''Constructor'''
    self.session = session

  def images(self, **kwargs) -> list:
    '''Query images

    :param kwargs: query args to pass
    :returns: list of images
    :raises RuntimeError: on error

    Will query and return a list images.  The list is cached
    within the process
    '''

    url = 'v2/images'
    while url:
      resp = self.session.get(self.api_path(url), params = kwargs)
      if kwargs: kwargs = dict()

      resp.raise_for_status()
      data = resp.json()

      # Yield images from this page
      for img in data.get('images',[]):
        yield img

      # Follow pagination
      url = data.get('next')



if __name__ == '__main__':
  import api
  import creds
  import yaml
  cfg = creds.creds(cloud_name = 'otc-eu-de')
  ic(cfg)
  # ~ api.http_logging(1)
  api = api.ApiSession(cfg, True)
  ims = Ims(api)
  for img in ims.images(__imagetype = 'gold'):
    print('{name} - {id}'.format(**img))


  # ~ for tt in api.tms.tags():
    # ~ print(tt['key'],'=',tt['value'])


  del(api)


