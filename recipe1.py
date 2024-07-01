#
# Test
#
#define openstack_logging False
#
# ~ import openstack

# ~ osc = openstack.connect(ypp.lookup('cloud'))
print('Yes')
print(ypp.lookup('cloud'))

for server in scullery.cloud().compute.servers():
  print(server)


