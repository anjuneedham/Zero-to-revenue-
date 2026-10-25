"""Owner-only authentication using Firebase Auth ID tokens.

The browser signs in with Firebase (Google provider recommended); the server
verifies the ID token and then checks the verified email against the single
configured owner. Fail closed: if OWNER_EMAIL or FIREBASE_PROJECT_ID is not
configured, nobody gets in. No password or secret is stored by this system.
"""

import json
import os
import time
import urllib.request

import jwt  # PyJWT

CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"


class AuthError(PermissionError):
    pass


def _fetch_certs() -> dict:
    with urllib.request.urlopen(CERTS_URL, timeout=10) as r:  # nosec - fixed https URL
        return json.load(r)


class OwnerAuth:
    def __init__(self, project_id: str | None = None, owner_email: str | None = None,
                 cert_fetcher=_fetch_certs, max_token_age: int = 3600):
        self.project_id = project_id or os.environ.get("FIREBASE_PROJECT_ID", "")
        self.owner_email = (owner_email or os.environ.get("OWNER_EMAIL", "")).strip().lower()
        self._fetch = cert_fetcher
        self.max_token_age = max_token_age

    def verify(self, id_token: str) -> str:
        """Return the verified owner email or raise AuthError."""
        if not self.project_id or not self.owner_email:
            raise AuthError("auth not configured")
        try:
            kid = jwt.get_unverified_header(id_token).get("kid")
            cert = self._fetch().get(kid)
            if not cert:
                raise AuthError("unknown signing key")
            from cryptography.x509 import load_pem_x509_certificate
            key = load_pem_x509_certificate(cert.encode()).public_key()
            claims = jwt.decode(
                id_token, key, algorithms=["RS256"], audience=self.project_id,
                issuer=f"https://securetoken.google.com/{self.project_id}",
                options={"require": ["exp", "iat", "aud", "iss", "sub"]})
        except AuthError:
            raise
        except Exception as e:  # any parse/signature/claim failure => deny
            raise AuthError(f"invalid token: {type(e).__name__}") from e
        if not claims.get("sub"):
            raise AuthError("missing subject")
        if time.time() - claims["iat"] > self.max_token_age + 60:
            raise AuthError("token too old")
        email = str(claims.get("email", "")).lower()
        if not claims.get("email_verified") or email != self.owner_email:
            raise AuthError("not the owner")
        return email
