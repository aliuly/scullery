'''
Tag management service implementation

'''

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa


class Tms:
  '''Tag management class'''
  API_HOST = 'tms.{region}.otc.t-systems.com'
  '''API end-point'''

  def api_path(self, path):
    '''API URL'''
    host = Tms.API_HOST.format(region = self.session.region)
    return f'https://{host}/{path}'

  def __init__(self, session) -> None:
    '''Constructor for Tms class'''
    self.session = session

  def tags(self) -> list:
    '''Returns a list of pre-defined tags

    :returns: list of predefined tags
    '''

    resp = self.session.get(self.api_path('v1.0/predefine_tags'))
    if resp.status_code != 200 or not 'tags' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['tags']

  def create(self,key:str, value:str):
    '''Create predefined tag

    :param key: predefined key name
    :param value: predefined value
    '''
    resp = self.session.post(self.api_path('v1.0/predefine_tags/action'), json = {
        'action': 'create',
        'tags': [ { 'key': key, 'value': value } ],
      })
    if resp.status_code != 204:
      raise RuntimeError(resp.reason if resp.text == '' else resp.text)

  def delete(self,key:str, value:str):
    '''Delete predefined tag

    :param key: predefined key name
    :param value: predefined value
    '''
    resp = self.session.post(self.api_path('v1.0/predefine_tags/action'), json = {
        'action': 'delete',
        'tags': [ { 'key': key, 'value': value } ],
      })
    if resp.status_code != 204:
      raise RuntimeError(resp.reason if resp.text == '' else resp.text)

if __name__ == '__main__':
  import api
  import creds
  cfg = creds.creds(cloud_name = 'otc-de-iam')
  api = api.ApiSession(cfg)

  for tt in api.tms.tags():
    print(tt['key'],'=',tt['value'])

  api.tms.create('project', 'test11')
  api.tms.delete('project', 'test11')

  del(api)

