# Cloud Config options

Refer to [openstack documentation][osdoccfg] and
[OTC Extensions SDK][otcsdkdoccfg] for the source
documents.

The recommended way is to use a `clouds.yaml` file in the
current directory.

Connections to Open Telekom Cloud and OpenStack clouds
are defined from environment variables or configuration
files.

This makes it possible to use the same configuration methods
from different client applications.

## Configuring via Environment variables

Instead of using a `clouds.yaml` file, environment variables can be
configured to connect to the Open Telekom Cloud. Create a simple file
like `.ostackrc` in the home directory and source the file to make
the variables available. On Open Telekom Cloud servers this file
exists on bootup and needs to be changed according to your credentials.

```bash
# .ostackrc file
export OS_USERNAME="<USER_NAME>"
export OS_USER_DOMAIN_NAME=<OTC00000000001000000XYZ>
export OS_PASSWORD=<PASSWORD> # optional
export OS_PROJECT_NAME=<eu-de_PROJECT_NAME>
# export OS_TENANT_NAME=eu-de
# export OS_AUTH_URL=https://iam.eu-de.otc.t-systems.com:443/v3
# export NOVA_ENDPOINT_TYPE=publicURL
# export OS_ENDPOINT_TYPE=publicURL
# export CINDER_ENDPOINT_TYPE=publicURL
# export OS_VOLUME_API_VERSION=2
# export OS_IDENTITY_API_VERSION=3
# export OS_IMAGE_API_VERSION=2
```

Run the source command to make the environment variables available.

```bash
$ source .ostackrc
```
The environment variables are now available for usage.

## Configuring via `clouds.yaml` file


To use a configuration file called `clouds.yaml` in one of the default
locations:

- Current Directory
- `~/.config/openstack`
- `/etc/openstack`

Alternatively, you can use a User Defined Location. To use a
configuration file in a user defined location set the environment
variable `OS_CLIENT_CONFIG_FILE` to the absolute path of a file:

```bash
export OS_CLIENT_CONFIG_FILE=/path/to/my/config/my-clouds.yaml
```

A sample clouds.yaml file is listed below to connect with Open
Telekom Cloud:

`clouds.yaml`

```yaml
clouds:
  otc: # self-defined and can be changed to any value
    profile: otc
    auth:
      user_domain_name: 'OTC00000000001000000xxx'
      username: '<USER_NAME>'
      password: '<PASSWORD>'
      # project_name: '<eu-de_project>'
      # or project_id: '<123456_PROJECT_ID>'
      # or user_domain_id: '<123456_DOMAIN_ID>'
      # auth_url: 'https://iam.eu-de.otc.t-systems.com:443/v3'
    # interface: 'public'
    # identity_api_version: 3 # !Important
    # ak: '<AK_VALUE>' # AK/SK pair for access to OBS
    # sk: '<SK_VALUE>'
```

AK/SK values required for access to some services (i.e. OBS) can
be either configured as shown above in the `clouds.yaml`/`secure.yaml`,
or they can be automatically retrieved from the `S3_ACCESS_KEY_ID`
and `S3_SECRET_ACCESS_KEY` environment variables.

### Additional projects

Additional connections to other Openstack-clouds or -projects can be added to the file as shown below:

`clouds.yaml`

```yaml
clouds:
  otcfirstproject:
    profile: otc
    auth:
      username: '<USER_NAME>'
      password: '<PASSWORD>'
      project_name: '<eu-de_project>'
      # or project_id: '<123456_PROJECT_ID>'
      user_domain_name: 'OTC00000000001000000xxx'
      # or user_domain_id: '<123456_DOMAIN_ID>'
      auth_url: 'https://iam.eu-de.otc.t-systems.com:443/v3'
    interface: 'public'
    identity_api_version: 3 # !Important
    ak: '<AK_VALUE>' # AK/SK pair for access to OBS
    sk: '<SK_VALUE>'
  otcsecondproject:
    profile: otc
    auth:
     username: '<USER_NAME>'
      password: '<PASSWORD>'
      project_name: '<eu-de_project2>'
      # or project_id: '<123456_PROJECT_ID2>'
      user_domain_name: 'OTC00000000001000000xxx'
      # or user_domain_id: '<123456_DOMAIN_ID2>'
      auth_url: 'https://iam.eu-de.otc.t-systems.com:443/v3'
    interface: 'public'
    identity_api_version: 3 # !Important
    ak: '<AK_VALUE>' # AK/SK pair for access to OBS
    sk: '<SK_VALUE>'
```

### Splitting the credentials in clouds.yaml and secure.yaml

In some scenarios a split of security credentials from the
configuration file is necessary. The optional file `secure.yaml`
can be used to store the secret which is left out from `clouds.yaml`:

`clouds.yaml`

```yaml
clouds:
  otc:
    profile: otc
    auth:
      username: '<USER_NAME>'
      project_name: '<eu-de_project>'
      # or project_id: '<123456_PROJECT_ID>'
      user_domain_name: 'OTC00000000001000000xxx'
      # or user_domain_id: '<123456_DOMAIN_ID>'
      auth_url: 'https://iam.eu-de.otc.t-systems.com:443/v3'
    interface: 'public'
    identity_api_version: 3 # !Important
    ak: '<AK_VALUE>' # AK/SK pair for access to OBS
    sk: '<SK_VALUE>'
```

`secure.yaml`

```yaml
clouds:
  otc:
    auth:
      password: '<PASSWORD>'
```



  [osdoccfg]: https://docs.openstack.org/openstacksdk/latest/user/guides/connect_from_config.html
  [otcsdkdoccfg]: https://docs.otc.t-systems.com/python-otcextensions/install/configuration.html#clouds-yaml
