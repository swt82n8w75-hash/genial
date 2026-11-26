"""Create the App Store provisioning profile for Geniality via the App Store Connect API."""
import base64, json, os, sys, time, urllib.error, urllib.parse, urllib.request

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

KEY_ID = os.environ["ASC_KEY_ID"]
ISSUER = os.environ["ASC_ISSUER_ID"]
KEY_PATH = os.path.expanduser(os.environ["ASC_KEY_PATH"])
BUNDLE = "com.toplinesupport.geniality"
PROFILE_NAME = "Geniality App Store"
OUT = os.path.expanduser("~/Library/MobileDevice/Provisioning Profiles/%s.mobileprovision" % PROFILE_NAME)


def b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


key = serialization.load_pem_private_key(open(KEY_PATH, "rb").read(), password=None)
now = int(time.time())
header = b64u(json.dumps({"alg": "ES256", "kid": KEY_ID, "typ": "JWT"}).encode())
claims = b64u(json.dumps({"iss": ISSUER, "iat": now, "exp": now + 900,
                          "aud": "appstoreconnect-v1"}).encode())
signing_input = header + "." + claims
der = key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256()))
r, s = decode_dss_signature(der)
token = signing_input + "." + b64u(r.to_bytes(32, "big") + s.to_bytes(32, "big"))


def api(path, method="GET", body=None):
    req = urllib.request.Request(
        "https://api.appstoreconnect.apple.com" + path, method=method,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body else None)
    return json.load(urllib.request.urlopen(req))


bids = api("/v1/bundleIds?filter[identifier]=%s&limit=5" % urllib.parse.quote(BUNDLE))["data"]
if not bids:
    sys.exit("bundle id %s is not registered with Apple" % BUNDLE)
bid = bids[0]["id"]
print("bundle id resource:", bid, bids[0]["attributes"]["identifier"])

certs = api("/v1/certificates?limit=200")["data"]
dist = [c for c in certs if c["attributes"]["certificateType"] in ("DISTRIBUTION", "IOS_DISTRIBUTION")]
print("distribution certificates:", [(c["id"], c["attributes"].get("displayName")) for c in dist])
if not dist:
    sys.exit("no distribution certificate on the account")
dist.sort(key=lambda c: c["attributes"].get("expirationDate") or "")
cert_id = dist[-1]["id"]
print("using certificate", cert_id, dist[-1]["attributes"].get("displayName"))

existing = api("/v1/profiles?filter[name]=%s&limit=5" % urllib.parse.quote(PROFILE_NAME))["data"]
if existing:
    pid = existing[0]["id"]
    print("profile already exists:", pid)
else:
    body = {"data": {"type": "profiles", "attributes": {
        "name": PROFILE_NAME, "profileType": "IOS_APP_STORE"}, "relationships": {
        "bundleId": {"data": {"type": "bundleIds", "id": bid}},
        "certificates": {"data": [{"type": "certificates", "id": cert_id}]}}}}
    made = api("/v1/profiles", "POST", body)["data"]
    pid = made["id"]
    print("profile created:", pid)

full = api("/v1/profiles/%s" % pid)["data"]["attributes"]["profileContent"]
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "wb").write(base64.b64decode(full))
print("wrote", OUT, os.path.getsize(OUT), "bytes")
