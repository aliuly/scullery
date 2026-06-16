#!python3
#
# OBS (Object Storage Service) bucket management
#

'''OBS Bucket API — list, create, and delete buckets.

The OBS API requires **AWS Signature V4** (AWS4-HMAC-SHA256) signing for
every request.  The signing headers are provided externally (via
:func:`tcurl.creds`) when constructing an :class:`~scullery.api.ObsSession`.

Credential acquisition (handled by :func:`~scullery.clouds.s3session`):

* If the session was created with **AK/SK** auth, those credentials are
  reused directly (converted to AWS4-HMAC-SHA256 headers by ``tcurl``).
* If the session uses **password** or **token** auth, a temporary AK/SK
  pair (with *security_token*) is obtained from IAM via ``tcurl.temp_aksk``
  before making any OBS call.

Usage::

    from scullery.clouds import s3session
    cc = s3session(args)
    buckets = cc.bucket.buckets()
    cc.bucket.create('my-new-bucket')
    cc.bucket.delete('my-old-bucket')
'''

import base64
import hashlib
import json
import magic
import xml.etree.ElementTree as ET
import re
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------

def _ns(root: ET.Element) -> str:
  '''Extract the XML namespace from *root* (or empty string).'''
  tag = root.tag
  if '}' in tag:
    return tag.split('}')[0].strip('{')
  return ''

def _text(parent: ET.Element | None, tag: str, ns: str = '') -> str:
  '''Return the text content of *tag* inside *parent*, or empty string.'''
  if parent is None:
    return ''
  child = parent.find(f'{{{ns}}}{tag}' if ns else tag)
  return child.text if child is not None else ''

# ---------------------------------------------------------------------------
# Location-constraint XML body builder
# ---------------------------------------------------------------------------

def _location_body(region: str) -> bytes:
  '''Build the ``CreateBucketConfiguration`` XML body.

  Required when creating a bucket in a region that differs from the
  endpoint's default region (per the S3 / OBS specification).
  '''
  # OBS namespace used for create-bucket config
  return (
      b'<CreateBucketConfiguration'
      b' xmlns="http://obs.otc.t-systems.com/doc/2014-01-01/">'
      b'<LocationConstraint>' + region.encode('utf-8') +
      b'</LocationConstraint>'
      b'</CreateBucketConfiguration>'
  )


# ---------------------------------------------------------------------------
# Objects class
# ---------------------------------------------------------------------------
class Objects:
  '''OBS Object management -- objects, upload, download
  '''
  def __init__(self, buckets, bucket) -> None:
    '''Constructor

    :param session: An :class:`~scullery.obs.Buckets` instance.
    '''
    self.buckets = buckets
    h = buckets.meta(bucket)
    # ~ ic(h)
    self.endpoint = h['endpoint']
    self.region = h['x-amz-bucket-region']
    self.default_storage_class = h['x-default-storage-class']
    self.obs_version = h['x-obs-version']
    # ~ ic(h)
    self.sse = buckets.get_encryption(bucket)
    # ~ ic(self.sse)

  def put(self,
          key:str,
          content:bytes,
          headers: dict[str,str]):
    '''Upload an object

    :param key: object key
    :param content: contents to upload
    :param headers: additional headers for the request.

    The following headers are calculated automatically if not
    provided by the caller:

    * Content-MD5: calculated from the object contents
    * Content-Type: if omitted, will be guessed using magic bytes
    * x-obs-server-side-encryption and x-obs-server-side-encryption-key-id :
      defaults to bucket settings.
    '''
    hdr = { k.lower(): v for k,v in headers.items() }
    if self.sse:
      if ('x-obs-server-side-encryption' not in hdr) and self.sse['algorithm'] == 'aws.kms':
        hdr['x-obs-server-side-encryption'] = 'kms'
      if ('x-obs-server-side-encryption-key-id' not in hdr) and 'kms_key_id' in self.sse:
        hdr['x-obs-server-side-encryption-key-id'] = self.sse['kms_key_id']
    if 'content-md5' not in hdr:
      md5_bytes = hashlib.md5(content).digest()
      hdr['content-md5'] = base64.b64encode(md5_bytes) #.decode('utf-8')?
    if 'content-type' not in hdr:
      hdr['content-type'] = magic.from_buffer(content, mime=True)

    resp = self.buckets.session.request('put', '/'+key,
              endpoint = self.endpoint,
              headers = hdr,
              data = content,
            )
    resp.raise_for_status()
    # ~ ic(resp, resp.headers, resp.content)

  def get(self,
          key:str,
          headers: dict[str,str]|None = None) -> bytes:
    '''Download an object

    :param key: object key
    :param headers: additional headers for the request.

    '''
    if headers is None: headers = dict()
    resp = self.buckets.session.request('get', '/'+key,
              endpoint = self.endpoint,
              headers = headers,
            )
    resp.raise_for_status()
    # ~ ic(resp, resp.headers)
    return resp.content

  def meta(self,
          key:str,
          headers: dict[str,str]|None = None) -> bytes:
    '''Get an object's metadata

    :param key: object key
    :param headers: additional headers for the request.

    '''
    if headers is None: headers = dict()
    resp = self.buckets.session.request('head', '/'+key,
              endpoint = self.endpoint,
              headers = headers,
            )
    resp.raise_for_status()
    # ~ ic(resp, resp.headers)
    return resp.headers

  def delete(self,
          key:str,
          headers: dict[str,str]|None = None) -> bytes:
    '''Delete an object

    :param key: object key
    :param headers: additional headers for the request.

    '''
    if headers is None: headers = dict()
    resp = self.buckets.session.request('delete', '/'+key,
              endpoint = self.endpoint,
              headers = headers,
            )
    resp.raise_for_status()
    # ~ ic(resp, resp.headers)

  def objects(self,
              prefix:str|None = None,
              delimiter:str = '/',
              fetch_owner:bool|None = None,
            ) -> list[dict[str,dict]]:
    '''Return a list of objects in the bucket
    :param bucket: bucket to query
    :param prefix: prefix string
    :param delimiter: defaults to "/"
    :param fetch_owner:
    :returns: list of objects
    :todo: Only supports 1000 key objects!
    '''
    params = {
        'list-type': 2,
        'delimiter': delimiter,
        # ~ 'max-keys': 5,
    }
    # ~ ic(self.endpoint)
    if prefix is not None: params['prefix'] = prefix
    if fetch_owner is not None: params['fetch-owner'] = 'true' if fetch_owner else 'false'

    resp = self.buckets.session.request('get','?', endpoint = self.endpoint, params = params)
    root = ET.fromstring(resp.content)
    namespace = _ns(root)

    objects: list[dict] = []

    prefix_tx = _text(root,'Prefix', namespace)
    key_count = _text(root,'KeyCount', namespace)
    key_count = int(key_count) if key_count.isdigit() else None
    is_trunc = _text(root,'IsTruncated', namespace) == 'true'

    contents = root.findall(f'{{{namespace}}}Contents' if namespace else 'Contents')
    for c in contents:
      size = _text(c,'Size',namespace)
      size = int(size) if size.isdigit() else None
      objects.append({
        'key': _text(c,'Key',namespace),
        'ETag': _text(c,'ETag',namespace).strip('"'),
        'size': size,
        'storage_class': _text(c,'StorageClass',namespace),
        'last_modified': _text(c,'LastModified',namespace),
      })
      owner = _text(c,'Owner',namespace)
      if owner: objects[-1]['owner'] = owner
    return objects

# ---------------------------------------------------------------------------
# Buckets class
# ---------------------------------------------------------------------------

class Buckets:
  '''OBS bucket management — buckets, create, delete, and ACL management.'''

  # Well-known group URIs for OBS ACLs.
  GROUP_ALL_USERS = 'http://acs.amazonaws.com/groups/global/AllUsers'
  '''All users group URI.'''
  GROUP_AUTHENTICATED_USERS = 'http://acs.amazonaws.com/groups/global/AuthenticatedUsers'
  '''Authenticated users group URI.'''

  # Valid ACL permissions.
  PERMISSIONS = frozenset({'READ', 'WRITE', 'READ_ACP', 'WRITE_ACP', 'FULL_CONTROL'})

  OBS_XML_NS = 'http://obs.otc.t-systems.com/doc/2014-01-01/'
  '''XML namespace used in OBS responses.'''

  XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'
  '''XML Schema Instance namespace (for grantee type attribute).'''


  def __init__(self, session) -> None:
    '''Constructor.

    :param session: An :class:`~scullery.api.ApiSession` instance.
    '''
    self.session = session


  # ------------------------------------------------------------------
  # Public API
  # ------------------------------------------------------------------
  def buckets(self) -> list[dict]:
    '''List all OBS buckets for the current project.

    :returns: List of dicts with keys ``name`` and ``creation_date``.
    :raises RuntimeError: On API errors.

    Calls ``GET /`` on the OBS endpoint and parses the XML response.
    '''
    resp = self.session.request('get', '/')
    # ~ ic(resp.content)
    root = ET.fromstring(resp.content)
    namespace = _ns(root)

    buckets: list[dict] = []
    buckets_elem = root.find(f'{{{namespace}}}Buckets' if namespace else 'Buckets')
    if buckets_elem is not None:
      for bucket_elem in buckets_elem.findall(
          f'{{{namespace}}}Bucket' if namespace else 'Bucket'
      ):
        buckets.append({
            'name': _text(bucket_elem, 'Name', namespace),
            'creation_date': _text(bucket_elem, 'CreationDate', namespace),

        })
    return buckets

  def create(self, name: str, location: str | None = None,
             kms_key_id: str | None = None) -> None:
    '''Create a new OBS bucket.

    :param name:     Bucket name (must be globally unique).
    :param location: Optional bucket location (region).  If omitted the
                     default region for the session is used.
    :param kms_key_id: Optional KMS key ID to enable SSE-KMS default
                       encryption on the bucket.
    :raises RuntimeError: On API errors.

    When *location* differs from the endpoint region (or when the
    endpoint region is not the default), the standard
    ``CreateBucketConfiguration`` XML body is included.
    '''
    headers: dict[str, str] = {}
    body: bytes | None = None

    obs_region = location or self.session.region

    # The S3 / OBS specification requires the location constraint
    # in the PUT body, not (just) a header.
    body = _location_body(obs_region)
    headers['Content-Type'] = 'application/xml'

    self.session.request('put', f'/{name}', headers=headers, data=body)
    if kms_key_id:
      # Enable encryption
      self.set_encryption(name, 'aws:kms', kms_key_id)

  def delete(self, name: str) -> None:
    '''Delete an OBS bucket.

    The bucket **must** be empty before it can be deleted.

    :param name: Bucket name.
    :raises RuntimeError: On API errors.
    '''
    self.session.request('delete', f'/{name}')

  # ------------------------------------------------------------------
  # Default encryption
  # ------------------------------------------------------------------

  def _parse_encryption(self, root: ET.Element) -> dict | None:
    '''Parse a ``ServerSideEncryptionConfiguration`` XML element.

    :param root: The root ``<ServerSideEncryptionConfiguration>`` element.
    :returns: A dict with keys ``algorithm`` and optionally ``kms_key_id``,
              or ``None`` if no rule is configured.
    '''
    ns = _ns(root) or Buckets.OBS_XML_NS
    rule = root.find(f'{{{ns}}}Rule' if ns else 'Rule')
    if rule is None:
      return None
    default = rule.find(
        f'{{{ns}}}ApplyServerSideEncryptionByDefault' if ns
        else 'ApplyServerSideEncryptionByDefault'
    )
    if default is None:
      return None
    result: dict = {
        'algorithm': _text(default, 'SSEAlgorithm', ns),
    }
    kid = _text(default, 'KMSMasterKeyID', ns)
    if kid:
      result['kms_key_id'] = kid
    return result

  def _build_encryption_xml(self,
                             algorithm: str,
                             kms_key_id: str | None = None) -> bytes:
    '''Build a ``ServerSideEncryptionConfiguration`` XML body.

    :param algorithm:  ``'AES256'`` or ``'aws:kms'``.
    :param kms_key_id: KMS key ID (required when *algorithm* is ``'aws:kms'``).
    :returns: XML bytes suitable for ``PUT /{bucket}?encryption``.
    '''
    ns = Buckets.OBS_XML_NS
    ET.register_namespace('', ns)

    root = ET.Element(f'{{{ns}}}ServerSideEncryptionConfiguration')
    rule = ET.SubElement(root, f'{{{ns}}}Rule')
    default = ET.SubElement(rule,
        f'{{{ns}}}ApplyServerSideEncryptionByDefault')
    alg = ET.SubElement(default, f'{{{ns}}}SSEAlgorithm')
    alg.text = algorithm
    if kms_key_id:
      kid = ET.SubElement(default, f'{{{ns}}}KMSMasterKeyID')
      kid.text = kms_key_id
    return ET.tostring(root, encoding='utf-8')

  def get_encryption(self, bucket: str) -> dict | None:
    '''Get the default encryption configuration for a bucket.

    :param bucket: Bucket name.
    :returns: A dict with ``algorithm`` and optionally ``kms_key_id``,
              or ``None`` if no default encryption is configured.
    :raises RuntimeError: On API errors other than 404.
    '''
    try:
      resp = self.session.request('get', f'/{bucket}?encryption')
    except RuntimeError as exc:
      if '404' in str(exc):
        return None
      raise
    root = ET.fromstring(resp.content)
    return self._parse_encryption(root)

  def set_encryption(self, bucket: str, algorithm: str,
                     kms_key_id: str | None = None) -> None:
    '''Set the default encryption configuration for a bucket.

    :param bucket:     Bucket name.
    :param algorithm:  ``'AES256'`` (SSE-S3) or ``'aws:kms'`` (SSE-KMS).
    :param kms_key_id: KMS key ID (required when *algorithm* is ``'aws:kms'``).
    :raises RuntimeError: On API errors.
    '''
    xml_body = self._build_encryption_xml(algorithm, kms_key_id=kms_key_id)
    headers = {'Content-Type': 'application/xml'}
    self.session.request('put', f'/{bucket}?encryption',
                         headers=headers, data=xml_body)

  def delete_encryption(self, bucket: str) -> None:
    '''Remove the default encryption configuration from a bucket.

    :param bucket: Bucket name.
    :raises RuntimeError: On API errors.
    '''
    self.session.request('delete', f'/{bucket}?encryption')

  # ------------------------------------------------------------------
  # ACL helpers
  # ------------------------------------------------------------------

  def _parse_acl(self, root: ET.Element) -> dict:
    '''Parse an ``AccessControlPolicy`` XML element into a structured dict.

    :param root: The root ``<AccessControlPolicy>`` element.
    :returns: A dict with keys ``owner`` and ``grants``.
    '''
    ns = _ns(root) or Buckets.OBS_XML_NS

    # -- Owner --
    owner_el = root.find(f'{{{ns}}}Owner' if ns else 'Owner')
    owner = {
        'id': _text(owner_el, 'ID', ns),
        'display_name': _text(owner_el, 'DisplayName', ns),
    }

    # -- Grants --
    grants: list[dict] = []
    acl_el = root.find(f'{{{ns}}}AccessControlList' if ns else 'AccessControlList')
    if acl_el is not None:
      for grant_el in acl_el.findall(
          f'{{{ns}}}Grant' if ns else 'Grant'
      ):
        grantee_el = grant_el.find(
            f'{{{ns}}}Grantee' if ns else 'Grantee'
        )
        grantee: dict = {}
        if grantee_el is not None:
          # Grantee type is stored as xsi:type attribute
          gtype = grantee_el.get(f'{{{Buckets.XSI_NS}}}type', 'CanonicalUser')
          grantee['type'] = gtype
          if gtype == 'CanonicalUser':
            grantee['id'] = _text(grantee_el, 'ID', ns)
            dn = _text(grantee_el, 'DisplayName', ns)
            if dn:
              grantee['display_name'] = dn
          elif gtype == 'Group':
            grantee['uri'] = _text(grantee_el, 'URI', ns)

        permission = _text(grant_el, 'Permission', ns)
        grants.append({
            'grantee': grantee,
            'permission': permission,
        })

    return {
        'owner': owner,
        'grants': grants,
    }

  def _build_acl_xml(self, acl: dict) -> bytes:
    '''Build an ``AccessControlPolicy`` XML body from a structured dict.

    :param acl: Dict with keys ``owner`` and ``grants`` (same format as
                returned by :meth:`_parse_acl`).
    :returns: XML bytes suitable for ``PUT /{bucket}?acl``.
    '''
    ns = Buckets.OBS_XML_NS
    xsi = Buckets.XSI_NS

    # Register namespaces so OBS accepts the XML — default namespace
    # without prefix, and xsi: for the type attribute.
    ET.register_namespace('', ns)
    ET.register_namespace('xsi', xsi)

    root = ET.Element(f'{{{ns}}}AccessControlPolicy')

    # -- Owner --
    owner_el = ET.SubElement(root, f'{{{ns}}}Owner')
    oid = ET.SubElement(owner_el, f'{{{ns}}}ID')
    oid.text = acl['owner']['id']
    if acl['owner'].get('display_name'):
      odn = ET.SubElement(owner_el, f'{{{ns}}}DisplayName')
      odn.text = acl['owner']['display_name']

    # -- AccessControlList --
    acl_el = ET.SubElement(root, f'{{{ns}}}AccessControlList')

    for grant in acl['grants']:
      grant_el = ET.SubElement(acl_el, f'{{{ns}}}Grant')
      grantee_el = ET.SubElement(grant_el, f'{{{ns}}}Grantee')
      gtype = grant['grantee']['type']
      grantee_el.set(f'{{{xsi}}}type', gtype)

      if gtype == 'CanonicalUser':
        gid = ET.SubElement(grantee_el, f'{{{ns}}}ID')
        gid.text = grant['grantee']['id']
        if grant['grantee'].get('display_name'):
          gdn = ET.SubElement(grantee_el, f'{{{ns}}}DisplayName')
          gdn.text = grant['grantee']['display_name']
      elif gtype == 'Group':
        guri = ET.SubElement(grantee_el, f'{{{ns}}}URI')
        guri.text = grant['grantee']['uri']

      perm = ET.SubElement(grant_el, f'{{{ns}}}Permission')
      perm.text = grant['permission']

    return ET.tostring(root, encoding='utf-8')

  # ------------------------------------------------------------------
  # ACL public API
  # ------------------------------------------------------------------

  def get_acl(self, bucket: str) -> dict:
    '''Get the Access Control List for a bucket.

    :param bucket: Bucket name.
    :returns: Dict with keys ``owner`` and ``grants`` (list of grant dicts).
    :raises RuntimeError: On API errors.

    Calls ``GET /{bucket}?acl`` on the OBS endpoint and parses the XML.
    '''
    resp = self.session.request('get', f'/{bucket}?acl')
    root = ET.fromstring(resp.content)
    return self._parse_acl(root)

  def set_acl(self, bucket: str, acl: dict) -> None:
    '''Set the Access Control List for a bucket.

    :param bucket: Bucket name.
    :param acl:    Dict with keys ``owner`` and ``grants`` (same format
                   as returned by :meth:`get_acl`).
    :raises RuntimeError: On API errors.

    Calls ``PUT /{bucket}?acl`` with the ACL XML body.
    '''
    xml_body = self._build_acl_xml(acl)
    headers = {'Content-Type': 'application/xml'}
    self.session.request('put', f'/{bucket}?acl', headers=headers, data=xml_body)

  def grant(self, bucket: str, grantee_type: str, grantee_id: str,
            permission: str, display_name: str | None = None) -> None:
    '''Grant a permission on a bucket.

    Reads the current ACL, appends the new grant (if not already present),
    and writes it back.

    :param bucket:       Bucket name.
    :param grantee_type: ``'CanonicalUser'`` or ``'Group'``.
    :param grantee_id:   For ``CanonicalUser``: the domain/account ID.
                         For ``Group``: the group URI (e.g.
                         ``http://acs.amazonaws.com/groups/global/AllUsers``).
    :param permission:   One of ``READ``, ``WRITE``, ``READ_ACP``,
                         ``WRITE_ACP``, ``FULL_CONTROL``.
    :param display_name: Optional display name (e.g. the original username).
                         Only meaningful for ``CanonicalUser`` grantees.
    :raises RuntimeError: On API errors.
    :raises ValueError:   On invalid grantee type or permission.
    '''
    if grantee_type not in ('CanonicalUser', 'Group'):
      raise ValueError(
          f'Invalid grantee type "{grantee_type}". '
          f'Expected "CanonicalUser" or "Group".'
      )
    if permission not in Buckets.PERMISSIONS:
      raise ValueError(
          f'Invalid permission "{permission}". '
          f'Valid values: {", ".join(sorted(Buckets.PERMISSIONS))}'
      )

    acl = self.get_acl(bucket)

    # Check if the exact grant already exists.
    for g in acl['grants']:
      if g['permission'] == permission and g['grantee'].get('type') == grantee_type:
        if grantee_type == 'CanonicalUser' and g['grantee'].get('id') == grantee_id:
          sys.stderr.write(f'Grant already exists for "{grantee_id}" with "{permission}\n".')
          return
        if grantee_type == 'Group' and g['grantee'].get('uri') == grantee_id:
          sys.stderr.write(f'Grant already exists for "{grantee_id}" with "{permission}\n".')
          return

    new_grant: dict
    if grantee_type == 'CanonicalUser':
      new_grant = {
          'grantee': {'type': 'CanonicalUser', 'id': grantee_id},
          'permission': permission,
      }
      if display_name:
        new_grant['grantee']['display_name'] = display_name
    else:
      new_grant = {
          'grantee': {'type': 'Group', 'uri': grantee_id},
          'permission': permission,
      }

    acl['grants'].append(new_grant)
    self.set_acl(bucket, acl)

  def revoke(self, bucket: str, grantee_type: str, grantee_id: str,
             permission: str) -> None:
    '''Revoke a permission from a bucket.

    Reads the current ACL, removes any matching grant, and writes it back.

    :param bucket:       Bucket name.
    :param grantee_type: ``'CanonicalUser'`` or ``'Group'``.
    :param grantee_id:   For ``CanonicalUser``: the domain/account ID.
                         For ``Group``: the group URI.
    :param permission:   One of ``READ``, ``WRITE``, ``READ_ACP``,
                         ``WRITE_ACP``, ``FULL_CONTROL``.
    :raises RuntimeError: On API errors.
    :raises ValueError:   On invalid grantee type or permission.
    '''
    if grantee_type not in ('CanonicalUser', 'Group'):
      raise ValueError(
          f'Invalid grantee type "{grantee_type}". '
          f'Expected "CanonicalUser" or "Group".'
      )
    if permission not in Buckets.PERMISSIONS:
      raise ValueError(
          f'Invalid permission "{permission}". '
          f'Valid values: {", ".join(sorted(Buckets.PERMISSIONS))}'
      )

    acl = self.get_acl(bucket)

    original_count = len(acl['grants'])
    acl['grants'] = [
        g for g in acl['grants']
        if not (
            g['permission'] == permission
            and g['grantee'].get('type') == grantee_type
            and (
                (grantee_type == 'CanonicalUser' and g['grantee'].get('id') == grantee_id)
                or (grantee_type == 'Group' and g['grantee'].get('uri') == grantee_id)
            )
        )
    ]

    if len(acl['grants']) == original_count:
      sys.stderr.write(f'No matching grant found for "{grantee_id}" with "{permission}".\n')
      return

    self.set_acl(bucket, acl)

  # ------------------------------------------------------------------
  # Tagging
  # ------------------------------------------------------------------

  def _parse_tagging(self, root: ET.Element) -> list[dict]:
    '''Parse a ``Tagging`` XML element into a list of ``{key, value}`` dicts.

    :param root: The root ``<Tagging>`` element.
    :returns: List of tag dicts.
    '''
    ns = _ns(root) or Buckets.OBS_XML_NS
    tag_set = root.find(f'{{{ns}}}TagSet' if ns else 'TagSet')
    if tag_set is None:
      return []

    tags: list[dict] = []
    for tag_el in tag_set.findall(f'{{{ns}}}Tag' if ns else 'Tag'):
      tags.append({
          'key': _text(tag_el, 'Key', ns),
          'value': _text(tag_el, 'Value', ns),
      })
    return tags

  def _build_tagging_xml(self, tags: list[dict]) -> bytes:
    '''Build a ``Tagging`` XML body from a list of ``{key, value}`` dicts.

    :param tags: List of tag dicts.
    :returns: XML bytes suitable for ``PUT /{bucket}?tagging``.
    '''
    ns = Buckets.OBS_XML_NS
    ET.register_namespace('', ns)

    root = ET.Element(f'{{{ns}}}Tagging')
    tag_set = ET.SubElement(root, f'{{{ns}}}TagSet')
    for tag in tags:
      tag_el = ET.SubElement(tag_set, f'{{{ns}}}Tag')
      k = ET.SubElement(tag_el, f'{{{ns}}}Key')
      k.text = tag['key']
      v = ET.SubElement(tag_el, f'{{{ns}}}Value')
      v.text = tag['value']
    return ET.tostring(root, encoding='utf-8')

  def get_tagging(self, bucket: str) -> list[dict]:
    '''Get the tags on a bucket.

    :param bucket: Bucket name.
    :returns: List of ``{'key': ..., 'value': ...}`` dicts.  Returns an
              empty list if the bucket has no tags.
    :raises RuntimeError: On API errors (other than 404 — no tags).
    '''
    try:
      resp = self.session.request('get', f'/{bucket}?tagging')
    except RuntimeError as exc:
      # OBS returns 404 when there are no tags at all.
      if '404' in str(exc):
          return []
      raise

    root = ET.fromstring(resp.content)
    return self._parse_tagging(root)

  def set_tagging(self, bucket: str, tags: list[dict]) -> None:
    '''Set the tags on a bucket (replaces any existing tags).

    :param bucket: Bucket name.
    :param tags:   List of ``{'key': ..., 'value': ...}`` dicts.
    :raises RuntimeError: On API errors.

    Calls ``PUT /{bucket}?tagging`` with the tagging XML body.
    '''
    xml_body = self._build_tagging_xml(tags)
    headers = {'Content-Type': 'application/xml'}
    self.session.request('put', f'/{bucket}?tagging', headers=headers, data=xml_body)

  def delete_tagging(self, bucket: str) -> None:
    '''Delete all tags from a bucket.

    :param bucket: Bucket name.
    :raises RuntimeError: On API errors.

    Calls ``DELETE /{bucket}?tagging``.
    '''
    self.session.request('delete', f'/{bucket}?tagging')

  # ------------------------------------------------------------------
  # Bucket policy (IAM user / group access)
  # ------------------------------------------------------------------

  POLICY_VERSION = '2008-10-17'
  '''The only policy version accepted by the OBS / S3 API.'''

  @staticmethod
  def _principal_urn(domain_id: str, principal_type: str, name: str) -> str:
    '''Build an IAM principal ARN for a user or group (S3-compatible format).

    :param domain_id:      The domain/account ID.
    :param principal_type: ``'user'`` or ``'group'``.
    :param name:           The IAM user or group name.
    :returns:              An ARN string suitable for use in a bucket
                           policy ``Principal`` element.
    '''
    return f'arn:aws:iam::{domain_id}:{principal_type}/{name}'

  @staticmethod
  def _bucket_arn(bucket: str) -> str:
    '''Build the OBS ARN for *bucket* and its objects (S3-compatible format).'''
    return f'arn:aws:s3:::{bucket}'

  @staticmethod
  def _object_arn(bucket: str) -> str:
    '''Build the OBS ARN for objects inside *bucket*.'''
    return f'arn:aws:s3:::{bucket}/*'

  @staticmethod
  def _permission_actions(permission: str) -> list[str]:
    '''Map a short permission name to a list of S3 actions.

    :param permission: ``'READ'``, ``'WRITE'``, or ``'FULL_CONTROL'``.
    :returns:          List of S3 action strings.
    :raises ValueError: On unknown permission.
    '''
    _MAP = {
        'READ': [
            's3:ListBucket',
            's3:GetObject',
            's3:GetObjectVersion',
        ],
        'WRITE': [
            's3:PutObject',
            's3:DeleteObject',
            's3:DeleteObjectVersion',
        ],
        'FULL_CONTROL': ['s3:*'],
    }
    if permission not in _MAP:
      raise ValueError(
          f'Unknown permission "{permission}". '
          f'Valid values: {", ".join(_MAP)}'
      )
    return _MAP[permission]

  def get_policy(self, bucket: str) -> dict:
    '''Get the bucket policy.

    :param bucket: Bucket name.
    :returns: The policy dict (empty policy ``{"Version":"2008-10-17","Statement":[]}``
              if no policy exists).
    :raises RuntimeError: On API errors other than 404.
    '''
    try:
      resp = self.session.request('get', f'/{bucket}?policy')
      return resp.json()
    except RuntimeError as exc:
      if '404' in str(exc):
        return {'Version': self.POLICY_VERSION, 'Statement': []}
      raise

  def set_policy(self, bucket: str, policy: dict) -> None:
    '''Set the bucket policy (replaces any existing policy).

    :param bucket: Bucket name.
    :param policy: Policy dict.
    :raises RuntimeError: On API errors.
    '''
    headers = ['Content-Type:application/json']
    self.session.request('put', f'/{bucket}?policy',
                  headers=headers, data=json.dumps(policy))

  def delete_policy(self, bucket: str) -> None:
    '''Delete the bucket policy.

    :param bucket: Bucket name.
    :raises RuntimeError: On API errors.
    '''
    self.session.request('delete', f'/{bucket}?policy')

  def grant_policy(self, bucket: str, principal_urn: str,
                   permission: str) -> None:
    '''Grant a permission to an IAM user or group via bucket policy.

    Reads the current policy, adds (or merges into) an ``Allow``
    statement for *principal_urn*, and writes it back.

    :param bucket:        Bucket name.
    :param principal_urn: The IAM user/group URN (see :meth:`_principal_urn`).
    :param permission:    ``'READ'``, ``'WRITE'``, or ``'FULL_CONTROL'``.
    :raises RuntimeError: On API errors.
    :raises ValueError:   On invalid permission.
    '''
    actions = self._permission_actions(permission)
    policy = self.get_policy(bucket)

    # Look for an existing Allow statement that matches this principal.
    found = False
    for stmt in policy['Statement']:
      if stmt.get('Effect') != 'Allow': continue

      principals = stmt.get('Principal', {}).get('AWS', [])
      if isinstance(principals, str):
        principals = [principals]
      if principal_urn in principals:
        # Merge actions into the existing statement.
        existing = set(stmt.get('Action', []))
        merged = existing | set(actions)
        if merged != existing:
          stmt['Action'] = list(merged)
          found = True
        break
    else:
      # No existing statement — append a new one.
      sid = f'Grant-{principal_urn.split(":")[-1]}-{permission}'
      policy['Statement'].append({
          'Sid': sid,
          'Effect': 'Allow',
          'Principal': {'AWS': [principal_urn]},
          'Action': actions,
          'Resource': [
              self._bucket_arn(bucket),
              self._object_arn(bucket),
          ],
      })
      found = True

    if found:
      self.set_policy(bucket, policy)
    else:
      sys.stderr.write(f'Permission "{permission}" already fully granted for '
              f'"{principal_urn}".\n')

  def revoke_policy(self, bucket: str, principal_urn: str,
                    permission: str) -> None:
    '''Revoke a permission from an IAM user or group via bucket policy.

    Reads the current policy, removes matching actions from the
    principal's ``Allow`` statement, and writes it back.  If the
    statement becomes empty it is removed entirely.

    :param bucket:        Bucket name.
    :param principal_urn: The IAM user/group URN.
    :param permission:    ``'READ'``, ``'WRITE'``, or ``'FULL_CONTROL'``.
    :raises RuntimeError: On API errors.
    :raises ValueError:   On invalid permission.
    '''
    actions = set(self._permission_actions(permission))
    policy = self.get_policy(bucket)
    changed = False

    for stmt in list(policy['Statement']):
      if stmt.get('Effect') != 'Allow': continue

      principals = stmt.get('Principal', {}).get('AWS', [])
      if isinstance(principals, str):
        principals = [principals]
      if principal_urn not in principals: continue

      current_set = set(stmt.get('Action', []))
      remaining_set = current_set - actions
      if remaining_set != current_set:
        changed = True
        if remaining_set:
          stmt['Action'] = list(remaining_set)
        else:
          policy['Statement'].remove(stmt)
      break

    if changed:
      if not policy['Statement']:
        self.delete_policy(bucket)
      else:
        self.set_policy(bucket, policy)
    else:
      sys.stderr.write(f'No matching grant found for "{principal_urn}" '
              f'with "{permission}".\n')

  # ------------------------------------------------------------------
  # Metadata
  # ------------------------------------------------------------------
  def meta(self, bucket:str):
    '''Get bucket meta data
    :param bucket: bucket name
    :returns: dictionary with bucket metadata
    '''
    resp = self.session.request('head', f'/{bucket}')
    # ~ ic(resp,resp.headers)
    region = resp.headers['x-amz-bucket-region']
    if resp.status_code == 301:
      # OK, call the actual location
      host = f'{bucket}.{self.session.API_HOST.format(region=region)}'
      resp = self.session.request('head','/', endpoint = host)
      headers = {
        'endpoint': host,
        'region': region,
      }
    else:
      headers = {
        'endpoint': f'{bucket}.{self.session.API_HOST.format(region=region)}',
        'region': region,
      }

    headers.update(resp.headers)
    return headers

  def objects(self, bucket:str):
    '''Objects class factory
    :param bucket: bucket we are working on
    :returns: Objects instances
    '''
    return Objects(self, bucket)


    # ~ ,
              # ~ prefix:str|None = None,
              # ~ delimiter:str = '/',
              # ~ fetch_owner:bool|None = None,
            # ~ ) -> list[dict[str,dict]]:
    # ~ '''Return a list of objects in the bucket
    # ~ :param bucket: bucket to query
    # ~ :param prefix: prefix string
    # ~ :param delimiter: defaults to "/"
    # ~ :param fetch_owner:
    # ~ :returns: list of objects
    # ~ :todo: Only supports 1000 key objects!
    # ~ '''
    # ~ h = self.meta(bucket)
    # ~ params = {
        # ~ 'list-type': 2,
        # ~ 'delimiter': delimiter,
        # ~ 'max-keys': 5,
    # ~ }
    # ~ if prefix is not None: params['prefix'] = prefix
    # ~ if fetch_owner is not None: params['fetch-owner'] = 'true' if fetch_owner else 'false'

    # ~ resp = self.session.request('get','?', endpoint = h['endpoint'], params = params)
    # ~ root = ET.fromstring(resp.content)
    # ~ namespace = _ns(root)
    # ~ objects: list[dict] = []

    # ~ prefix_tx = _text(root,'Prefix', namespace)
    # ~ key_count = _text(root,'KeyCount', namespace)
    # ~ key_count = int(key_count) if key_count.isdigit() else None
    # ~ is_trunc = _text(root,'IsTruncated', namespace) == 'true'

    # ~ contents = root.findall(f'{{{namespace}}}Contents' if namespace else 'Contents')
    # ~ for c in contents:
      # ~ size = _text(c,'Size',namespace)
      # ~ size = int(size) if size.isdigit() else None
      # ~ objects.append({
        # ~ 'key': _text(c,'Key',namespace),
        # ~ 'ETag': _text(c,'ETag',namespace).strip('"'),
        # ~ 'size': size,
        # ~ 'storage_class': _text(c,'StorageClass',namespace),
        # ~ 'last_modified': _text(c,'LastModified',namespace),
      # ~ })
      # ~ owner = _text(c,'Owner',namespace)
      # ~ if owner: objects[-1]['owner'] = owner
    # ~ return objects

if __name__ == '__main__':
  # Standalone test — requires a configured clouds.yaml with 'otc' cloud.
  # See docs/config.md for details.
  from scullery.clouds import s3session
  import argparse

  args = argparse.Namespace(
      project=None, region='eu-de',
      token=None, ak=None, sk=None, securitytoken=None,
      username=None, password=None, user_domain_name=None,
  )
  obs = s3session(args)
  buckets = obs.bucket.buckets()
  for b in buckets:
    print(b['name'], b['creation_date'])
