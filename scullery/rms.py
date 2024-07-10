try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa


class Rms:
  API_HOST = 'rms.{region}.otc.t-systems.com'

  def api_path(self, path):
    host = Rms.API_HOST.format(region = self.session.region)
    return f'https://{host}/{path}'

  def __init__(self, session) -> None:
    self.session = session

  def resources(self, match:str|None = None, typestr:str|None = None) -> list:
    '''List resources

    :param match: If specified, it will only return projects/region matching
    :param typestr: Specify a provider.type to select

    See: https://docs.otc.t-systems.com/resource-management-service/api-ref/apis/resource_query/querying_all_resources_under_your_account.html
    '''
    params = {
      'limit': 199
    }
    if not typestr is None: params['type'] = typestr


    domain_id = self.session.iam.domain(match)
    if not match is None:
      if '_' in match:
        params['region_id'], _ = match.split('_',1)
      else:
        params['region_id'] = match
        match = None

    resources = []

    while not 'marker' in params or not params['marker'] is None:
      resp = self.session.get(self.api_path(f'v1/resource-manager/domains/{domain_id}/all-resources'), params = params)
      if resp.status_code != 200 or not 'resources' in resp.json():
        raise RuntimeError(resp.text)
      q = resp.json()
      params['marker'] = q['page_info']['next_marker']

      if match is None:
        resources.extend(q['resources'])
      else:
        for r in q['resources']:
          if r['project_name'] == match: resources.append(r)

    return resources


if __name__ == '__main__':
  import api
  import creds
  import json

  cfg = creds.creds(cloud_name = 'otc-de-iam')
  api = api.ApiSession(cfg)
  res = api.rms.resources()
  print(json.dumps(res,indent=2))

  del(api)


