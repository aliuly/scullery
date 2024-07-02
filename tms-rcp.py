#
# Test
#
#define openstack_logging False
#
import openstack
import otcextensions.sdk

openstack.enable_logging(True)
conn = openstack.connect(cloud='otc')
otcextensions.sdk.register_otc_extensions(conn)

for tag in conn.tms.predefined_tags():
  print(tag)

