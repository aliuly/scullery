#
# New project recipe
#
import json
import sys
from scullery import cloud

# TODO add domain_id to iam

cc = cloud()

domain = None
region = 'eu-de'
q = cc.iam.projects()
# ~ print(json.dumps(q,indent=2))
for p in q:
  if p['name'] == region:
    domain = p['domain_id']
    break

api_url = f'https://rms.{region}.otc.t-systems.com/v1/resource-manager/domains/{domain}/all-resources'

loop_ctl = {
  'limit': 4,
}

resources = []
while not 'marker' in loop_ctl or not loop_ctl['marker'] is None:
  print(loop_ctl)
  resp = cc.get(api_url, params = loop_ctl)
  if resp.status_code != 200 or not 'resources' in resp.json():
    raise RuntimeError(resp.text)
  q = resp.json()
  loop_ctl['marker'] = q['page_info']['next_marker']
  if region is None:
    resources.extend(q['resources'])
  else:
    for r in q['resources']:
      if r['region_id'] == region: resources.append(r)
  print(json.dumps(q['page_info'],indent=2))

print(json.dumps(resources,indent=2))
