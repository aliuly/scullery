# NOTES

## ADRs

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

