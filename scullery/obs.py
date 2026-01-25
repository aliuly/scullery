'''
vibe coded
'''
import hmac
import hashlib
import base64
from datetime import datetime
import requests

def signature(ak, sk, method, bucket, object_key, headers=None):
    if headers is None:
        headers = {}

    # OBS requires a Date header
    if "Date" not in headers:
        headers["Date"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    # Canonicalize headers
    canonical_headers = ""
    for k, v in sorted(headers.items()):
        lk = k.lower()
        if lk.startswith("x-obs-"):
            canonical_headers += f"{lk}:{v}\n"

    # Canonical resource
    resource = f"/{bucket}/{object_key}"

    # Build string to sign
    string_to_sign = (
        f"{method}\n"
        f"{headers.get('Content-MD5', '')}\n"
        f"{headers.get('Content-Type', '')}\n"
        f"{headers['Date']}\n"
        f"{canonical_headers}{resource}"
    )

    # HMAC-SHA1
    digest = hmac.new(sk.encode(), string_to_sign.encode(), hashlib.sha1).digest()
    signature = base64.b64encode(digest).decode()

    # Authorization header
    auth_header = f"OBS {ak}:{signature}"

    return auth_header, headers

def upload(srcfile, ak, sk, token, bucket, object_key, headers = None):
  if headers is None: headers = dict()
  for k,v in {
        "Content-Type": "application/octet-stream",
        "x-obs-security-token": token
      }.items():
    if not k in headers: headers[k] = v

  auth, signed_headers = signature(ak, sk, method, bucket, object_key, headers)
  signed_headers["Authorization"] = auth


  with open(srcfile, "rb") as f:
    resp = requests.put(
        f"https://{bucket}.obs.eu-de.otc-t-systems.com/{object_key}",
        data=f,
        headers=signed_headers
    )

  print(resp.status_code, resp.text)
