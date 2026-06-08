'''
Key Management Service v1.0 API client

Provides a Python wrapper around the Open Telekom Cloud KMS REST API (v1.0).
'''
import sys

try:
  from icecream import ic
except ImportError:
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa


# ── State constants ───────────────────────────────────────────────────

STATE_PENDING_CREATION = 1
STATE_ENABLED          = 2
STATE_DISABLED         = 3
STATE_PENDING_DELETION = 4
STATE_PENDING_IMPORT   = 5

STATE_NAMES = {
  STATE_PENDING_CREATION: 'Pending creation',
  STATE_ENABLED:          'Enabled',
  STATE_DISABLED:         'Disabled',
  STATE_PENDING_DELETION: 'Pending deletion',
  STATE_PENDING_IMPORT:   'Pending import',
}

STATE_BY_NAME = {v.lower(): k for k, v in STATE_NAMES.items()}


# ── KMS client ───────────────────────────────────────────────────────

class Kms:
  '''KMS (Key Management Service) client using the v1.0 REST API.

  All operations require a project-scoped session.  If no project is
  provided at session creation, the current region is used as the
  project scope (see :meth:`scullery.api.ApiSession.project_id`).
  '''
  API_HOST = 'kms.{region}.otc.t-systems.com'
  '''API endpoint template.'''

  def __init__(self, session) -> None:
    '''Constructor.

    :param session: An authenticated :class:`scullery.api.ApiSession`.
    '''
    self.session = session
    self._prj_id = None

  # ── URL helpers ──────────────────────────────────────────────────

  def api_path(self, path: str = '') -> str:
    '''Build a full KMS API URL for *path*.'''
    host = Kms.API_HOST.format(region=self.session.region)
    return f'https://{host}/{path}'

  @property
  def project_id(self) -> str:
    '''Lazily resolve and cache the project / region ID.'''
    if self._prj_id is None:
      self._prj_id = self.session.project_id()
    return self._prj_id

  def _keys_base(self, action: str = '') -> str:
    '''Base URL for v1.0 key actions: ``/v1.0/{project_id}/kms/{action}``.'''
    return self.api_path(f'v1.0/{self.project_id}/kms/{action}')

  # ── Key lookup ───────────────────────────────────────────────────

  def resolve_key(self, name: str) -> str:
    '''Resolve a key alias or key ID to a key ID.

    Tries the following strategies in order:

    1. If *name* looks like a UUID, try :meth:`describe` directly.
    2. List all keys and match by ``key_alias``.
    3. Try :meth:`describe` one more time as a fallback.

    :param name:  Key alias or key ID.
    :returns:     The canonical key ID.
    :raises KeyError:  If no key matches.
    :raises RuntimeError:  If multiple keys share the same alias.
    '''
    # Fast path: input looks like a UUID.
    if len(name) >= 32 and '-' in name:
      try:
        return self.describe(name)['key_id']
      except RuntimeError:
        pass

    # Alias lookup.
    all_keys = self.keys()
    matches = [k for k in all_keys if k.get('key_alias') == name]
    if len(matches) == 1:
      return matches[0]['key_id']
    if len(matches) > 1:
      raise KeyError(f'Multiple keys match alias "{name}"')

    # Last chance: maybe a short / partial ID.
    try:
      return self.describe(name)['key_id']
    except RuntimeError:
      pass

    raise KeyError(f'No key found matching "{name}"')

  # ── Key lifecycle ────────────────────────────────────────────────

  def keys(self, key_state: int | None = None,
           limit: int = 2000, marker: str | None = None) -> list:
    '''List Customer Master Keys via the v1.0 ``list-keys`` endpoint.

    :param key_state:  Optional numeric state filter (see :data:`STATE_NAMES`).
    :param limit:      Maximum number of keys to return (default 2000).
    :param marker:     Pagination marker for the next page.
    :returns:          List of key info dicts.
    :raises RuntimeError:  On API error.
    '''
    payload: dict = {'limit': str(limit)}
    if marker is not None:
      payload['marker'] = marker
    if key_state is not None:
      payload['key_state'] = str(key_state)
    resp = self.session.post(self._keys_base('list-keys'), json=payload)
    if resp.status_code != 200:
      raise RuntimeError(resp.text)
    data = resp.json()
    if 'key_details' not in data and 'keys' not in data:
      raise RuntimeError(resp.text)
    # v1.0 returns key_details; v2-style returns keys directly.
    keys = data.get('key_details', data.get('keys', []))
    for k in keys:
      k.setdefault('scheduled_deletion_date', '')
      k.setdefault('key_description', '')
      k.setdefault('key_alias', '')
      # Normalize key_state: v1.0 returns string codes like "2".
      ks = k.get('key_state', '')
      if isinstance(ks, str) and ks.isdigit():
        k['key_state'] = int(ks)
      # Normalize creation_date: v1.0 returns epoch milliseconds.
      cd = k.get('creation_date', '')
      if isinstance(cd, str) and cd.isdigit():
        try:
          from datetime import datetime, timezone
          dt = datetime.fromtimestamp(int(cd) / 1000, tz=timezone.utc)
          k['creation_date'] = dt.strftime('%Y-%m-%d')
        except (ValueError, OSError):
          pass
    return keys

  def describe(self, key_id: str) -> dict:
    '''Get full metadata for a key via the v1.0 ``describe-key`` endpoint.

    :param key_id:  Key ID.
    :returns:       Key info dict.
    :raises RuntimeError:  On API error.
    '''
    resp = self.session.post(self._keys_base('describe-key'),
                              json={'key_id': key_id})
    if resp.status_code != 200 or 'key_info' not in resp.json():
      raise RuntimeError(resp.text)
    info = resp.json()['key_info']
    info.setdefault('scheduled_deletion_date', '')
    info.setdefault('key_description', '')
    info.setdefault('key_alias', '')
    info.setdefault('rotation_enabled', False)
    info.setdefault('rotation_interval', 0)
    return info

  def create(self, alias: str, description: str | None = None,
             key_spec: str = 'AES_256',
             key_usage: str = 'ENCRYPT_DECRYPT') -> dict:
    '''Create a new Customer Master Key via the v1.0 ``create-key`` endpoint.

    :param alias:       Key alias (display name).
    :param description: Optional description.
    :param key_spec:    Key spec (``'AES_256'``, ``'AES_128'``, etc.).
    :param key_usage:   Key usage (``'ENCRYPT_DECRYPT'``, ``'SIGN_VERIFY'``).
    :returns:           Created key info dict.
    :raises RuntimeError:  On API error.
    '''
    payload: dict = {'key_alias': alias,
                     'key_spec': key_spec,
                     'key_usage': key_usage}
    if description:
      payload['key_description'] = description
    resp = self.session.post(self._keys_base('create-key'), json=payload)
    if resp.status_code != 200 or 'key_info' not in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['key_info']

  def schedule_deletion(self, key_id: str, pending_days: int = 7) -> dict:
    '''Schedule a key for deletion via the v1.0 ``schedule-key-deletion`` endpoint.

    :param key_id:       Key ID.
    :param pending_days: Days before permanent deletion (7–1096, default 7).
    :returns:            Updated key info dict (includes deletion date).
    :raises RuntimeError:  On API error.
    '''
    resp = self.session.post(self._keys_base('schedule-key-deletion'),
                              json={'key_id': key_id,
                                    'pending_days': str(pending_days)})
    ic(resp.status_code)
    ic(resp.json())
    if resp.status_code != 200: raise RuntimeError(resp.text)
    return resp.json()

  def cancel_deletion(self, key_id: str) -> dict:
    '''Cancel a scheduled key deletion via the v1.0 ``cancel-key-deletion`` endpoint.

    :param key_id:  Key ID.
    :returns:       Key info dict (may be empty on some API versions).
    :raises RuntimeError:  On API error.
    '''
    resp = self.session.post(self._keys_base('cancel-key-deletion'),
                              json={'key_id': key_id})
    if resp.status_code not in (200, 204):
      raise RuntimeError(resp.text if resp.text else resp.reason)
    return resp.json().get('key_info', {}) if resp.text else {}

  def enable(self, key_id: str) -> dict:
    '''Enable a disabled key via the v1.0 ``enable-key`` endpoint.

    :param key_id:  Key ID.
    :returns:       Key info dict (may be empty on some API versions).
    :raises RuntimeError:  On API error.
    '''
    resp = self.session.post(self._keys_base('enable-key'),
                              json={'key_id': key_id})
    if resp.status_code not in (200, 204):
      raise RuntimeError(resp.text if resp.text else resp.reason)
    return resp.json().get('key_info', {}) if resp.text else {}

  def disable(self, key_id: str) -> dict:
    '''Disable an enabled key via the v1.0 ``disable-key`` endpoint.

    :param key_id:  Key ID.
    :returns:       Key info dict (may be empty on some API versions).
    :raises RuntimeError:  On API error.
    '''
    resp = self.session.post(self._keys_base('disable-key'),
                              json={'key_id': key_id})
    if resp.status_code not in (200, 204):
      raise RuntimeError(resp.text if resp.text else resp.reason)
    return resp.json().get('key_info', {}) if resp.text else {}

  def get_rotation_status(self, key_id: str) -> dict:
    '''Query key rotation status via the v1.0 ``get-key-rotation-status`` endpoint.

    :param key_id:  Key ID.
    :returns:       Dict with ``key_rotation_enabled`` and ``rotation_interval``.
    :raises RuntimeError:  On API error.
    '''
    resp = self.session.post(self._keys_base('get-key-rotation-status'),
                              json={'key_id': key_id})
    if resp.status_code != 200:
      raise RuntimeError(resp.text)
    data = resp.json()
    return {
      'key_rotation_enabled': data.get('key_rotation_enabled', False),
      'rotation_interval': data.get('rotation_interval', 0),
    }

  def rotate(self, key_id: str, period: int | None = None) -> dict:
    '''Enable or disable automatic key rotation via the v1.0 endpoints.

    - ``period > 0``: enable rotation, then set interval.
    - ``period == 0``: disable rotation.
    - ``period is None``: return current status (no change).

    Enabling is a two-step process: first ``enable-key-rotation``,
    then ``update-key-rotation-interval``.  Disabling is a single call
    to ``disable-key-rotation``.

    :param key_id:  Key ID.
    :param period:  Rotation interval in days (30–365); 0 to disable;
                    None to just query current status.
    :returns:       Dict with ``key_rotation_enabled`` and ``rotation_interval``.
    :raises RuntimeError:  On API error.
    '''
    if period is None:
      return self.get_rotation_status(key_id)

    if period <= 0:
      resp = self.session.post(self._keys_base('disable-key-rotation'),
                                json={'key_id': key_id})
      if resp.status_code not in (200, 204):
        raise RuntimeError(resp.text if resp.text else resp.reason)
      return {'key_rotation_enabled': False, 'rotation_interval': 0}

    # Enable rotation first.
    resp = self.session.post(self._keys_base('enable-key-rotation'),
                              json={'key_id': key_id})
    if resp.status_code not in (200, 204):
      raise RuntimeError(resp.text if resp.text else resp.reason)

    # Then set the interval.
    resp = self.session.post(self._keys_base('update-key-rotation-interval'),
                              json={'key_id': key_id,
                                    'rotation_interval': period})
    if resp.status_code not in (200, 204):
      raise RuntimeError(resp.text if resp.text else resp.reason)

    return {'key_rotation_enabled': True, 'rotation_interval': period}

