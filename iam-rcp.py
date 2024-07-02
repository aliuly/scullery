#
# Test
#
#define openstack_logging False
#
import openstack

# ~ openstack.enable_logging(True)
cc = openstack.connect(cloud='otc')

# Broken?
for i in cc.identity.policies():
  print(i)

# This is OK
for i in cc.identity.projects():
  print('{id} {name:16} {description}'.format(**i))

# Permission?
for i in cc.identity.groups():
  print(i)

# Permisison
for i in cc.identity.roles():
  print(i)

#  This is OK
for i in cc.identity.services():
  print('{id} {name:16} {type}'.format(**i))

# Permission
for i in cc.identity.users():
  print(i)

# Permission
for i in cc.identity.agencies():
  print(i)

# OK
for i in cc.identity.regions():
  print('{id}'.format(**i))
  
