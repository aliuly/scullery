#
#
#

cc = cloud(cloud_name='otc-iam')


for server in cc.compute.servers():
    print(server)
