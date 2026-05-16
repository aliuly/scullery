# NOTES

## Authentication

This is meant for interactive use only, so the flow, user logs in at
the beginning of session, and uses things.  Provides unscoped
credentials.

We do not do TF or OpenStack-cli integration.  We do that using
`tcurl`.

```
command line -> environment -> clouds.yaml in directory -> clouds.yaml in user dir
```

Command line

* token (assummed unscoped)
* ak/sk
* username+password

enviroment

* OS_AUTH_TOKEN ... OS_AUTH_USER_ID or OS_AUTH_DOMAIN_ID ! OS_AUTH_PROJECT_ID
Or ...
* OS_USERNAME
* OS_USER_DOMAIN_NAME
* OS_PASSWORD
* OS_TENANT_NAME or OS_REGION (defaults to eu-de)
Or...
* OS_ACCESS_KEY, OS_SECRET_KEY and optional OS_SECURITY_TOKEN

And only if all if it is a complete set.

Config files:
- /etc/openstack/{clouds,secure}.yaml
- ~/.config/openstack/{clouds,secure}.yaml
- current dir ./{clouds,secure}.yaml)

If using clouds.yaml

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
Will only look for `scullery` as the project key.

Show a warning if user has OS_TENANT_NAME or OS_PROJECT_NAME
or has (clouds)(scullery)(auth)(project_name) defined in clouds.yaml
and a scope is requested on command line.

## AUTH

Interaction via [prompt-toolkit][prompt-toolkit] or
[questionary][questionary].

YAML editiing via [ruamel.yaml][ruamel].
INI editing via [configupdater][configupdater]

* login - configures ~/.config/openstack ... Default `scullery` key.
  * **Ignores** environment when configuring but uses it for defaults
  in interactive mode.
  * Configuration either via CLI or interactive.
* s3login - configures ~/.s3cfg.
  * uses user-name to issue temp AK/SK
  * interactively inputs a permanent AK/SK and configures s3cfg
  ```ini
  [default]
  access_key = <your-temporary-AK>
  secret_key = <your-temporary-SK>
  access_token = <your-security-token>

  host_base = obs.eu-de.otc.t-systems.com
  host_bucket = %(bucket)s.obs.eu-de.otc.t-systems.com

  use_https = True
  signature_v2 = False

  region = eu-de
  ```



***

# TODO

- [x] format specification/JSON/YAML
- [x] Terraform-compatible authentication (password, token, AK/SK, agency)
- [x] kurotc ops -- shouldn't require admin access
  - start, stop, list-status
- [x] list flavors, deh types
- [x] list OS images
- [x] Include curler as a recipe
- [x] Better table output
- [x] reset password
  - seems to work *once* and need to wait before re-use.
- [x] manage OBS buckets
- [x] Add `--scope` option so that we can choose the project scope
***
- [ ] Revamp the credential workflow
- [ ] Get temp AK/SK/Token
  - login like functionality.  Input username/password and updating
    .config/openstack/clouds.yaml file.
- [ ] Phase out kermit -> terraform project factory pattern
  - https://github.com/iits-consulting/terraform-opentelekomcloud-project-factory
  - https://github.com/iits-consulting/terraform-opentelekomcloud-projects
  - Waiting for CASIO Closure

# ADRs

- Functionality that can be done on TerraForm not to be replicated.
  - i.e. kermit recipes
- Functionality that can be done with S3cmd not to be replicated.  But maybe
  something to login to s3cmd would be good.  (Writting to s3cmd config)
- Will **NOT** implement agency authentication
- Will **NOT** implement Federated Identity support
- will **NOT** import OS images, assuming an existing OBS object.
  This is possible from Terraform.  TF supports the full
  cycle, including creating buckets, upload object etc.
- Will **NOT** issue Terraform or Environment configs.  We will use
  `tcurl` to generate Env variables.  This allow us to configure
  terraform with empty provider blocks. (HCL needs the provider blocks
  to refer to the variables).


  [osstd]: https://python-otcextensions.readthedocs.io/en/latest/install/configuration.html
  [ruamel]: https://pypi.org/project/ruamel.yaml/
  [questionary]: https://pypi.org/project/questionary/
  [prompt-toolkit]: https://pypi.org/project/prompt-toolkit/
  [configupdater]: https://pypi.org/project/ConfigUpdater/

