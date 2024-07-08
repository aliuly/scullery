#
# Roles recipe
#
import json
import sys

from scullery import cloud

kermit_role = 'ACME-kermit-operator'

print(argv)
cc = cloud()

if len(argv) == 1 and argv[0] == 'register':
  new_role = cc.iam.new_role(display_name = kermit_role, policy = [
          { 'Action': ['ecs:*:get*',
                        'ecs:*:list*',
                        'ecs:*:stop*',
                        'ecs:*:start*',
                        'ecs:*:reboot*'],
             'Effect': 'Allow'}])
  print(json.dumps(new_role, indent=2))
else:
  print('Usage')
  print('register : register kermit roles')
