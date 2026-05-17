# scullery

Utility for executing Cloud related recipes

Most of the recipes in **scullery** require admin access.

## Authentication

**scullery** accepts authentication credentials as:

```
command line -> environment -> configuration files
```

Via command line it accepts in order of preference:

* token (assumed to be either unscoped or of the appropriate scope)
* ak/sk
* username+password

Via environment:

* token
  * OS_AUTH_TOKEN ... OS_AUTH_USER_ID or OS_AUTH_DOMAIN_ID ! OS_AUTH_PROJECT_ID
* ak/sk
  * OS_ACCESS_KEY, OS_SECRET_KEY and optional OS_SECURITY_TOKEN
* username+password
  * OS_USERNAME
  * OS_USER_DOMAIN_NAME
  * OS_PASSWORD

Configuration files:

- /etc/openstack/{clouds,secure}.yaml
- ~/.config/openstack/{clouds,secure}.yaml
- current dir ./{clouds,secure}.yaml)

For files, the configuration template is as follows:

```yaml
clouds:
  scullery:
    auth:
      username: '<USER_NAME>'
      password: '<PASSWORD>'
      user_domain_name: 'OTC00000000001000000xxx'
```
or

```yaml
clouds:
  scullery:
    ak: <AK_VALUE>
    sk: <AK_VALUE>
```

**NOTE**: only the key `scullery` is recognized.  Any other values
will be ignored.

This configuration is mostly similar to [python-otcextensions][osstd]
configuration files.

**scullery** will also use this file to store cached credentials when
appropriate.

## Available Recipes

| Command | Module | Description |
|---------|--------|-------------|
| `scullery bucket` | `rcp_buckets.py` | **OBS** – list, create, delete buckets; manage tags and access policies |
| `scullery wiz` | rcp_cfgwiz.py | Configuration wizard to interactively setup **scullery** |
| `scullery deh` | `rcp_deh.py` | List available **Dedicated Host** types |
| `scullery ecs` | `rcp_ecs.py` | **ECS** – list, inspect, start, stop, reboot servers; query flavors |
| `scullery group` | `rcp_groups.py` | **IAM Groups** – list, get details, create, delete |
| `scullery image` | `rcp_ims.py` | **IMS** – list and filter images, get image details |
| `scullery login` | `rcp_login.py` | **login/logout** - Login/logout sessions |
| `scullery project` | `rcp_projects.py` | **Project** – list, get details, create, delete, grant/revoke role assignments |
| `scullery resource` | `rcp_rms.py` | **RMS** – list cloud resources, optionally filtered by project |
| `scullery role` | `rcp_roles.py` | **IAM Roles** – list custom/system roles, get details, create, delete |
| `scullery tag` | `rcp_tms.py` | **TMS** – list, create, delete pre-defined tags |
| `scullery user` | `rcp_users.py` | **IAM Users** – list, get, create, delete; manage group membership and passwords |

Run any recipe with `-h` / `--help` for full usage details.

  [osstd]: https://python-otcextensions.readthedocs.io/en/latest/install/configuration.html
