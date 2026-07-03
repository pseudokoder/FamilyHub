"""security_service — the settings-driven password baseline (Master Plan §9).

Two jobs, both read live from ``site_settings`` so an admin tunes them without a
deploy:
  * **Length** — reject passwords shorter than ``min_password_length``.
  * **Breach check** — when ``breach_check_enabled`` is on, reject passwords that
    appear in the Have I Been Pwned corpus, checked via **k-anonymity**: we hash
    the password with SHA-1, send only the first 5 hex chars of the hash to the
    API, and scan the returned suffixes locally. The full password (and full hash)
    NEVER leave this process — that's the whole point of the range query (D315).

FAIL-OPEN on network trouble: if HIBP is unreachable, we DON'T block the user from
setting a password (availability > a nice-to-have check). The length rule always
applies regardless.

v2 mapping: a ``PasswordPolicyService`` reading the same settings; the HIBP call
becomes a small ``RestClient`` bean (still k-anonymity).
"""

import hashlib
import urllib.request

from app.services import settings_service

_HIBP_RANGE_URL = "https://api.pwnedpasswords.com/range/"
_TIMEOUT_SECONDS = 3


def _fetch_hibp_range(prefix):
    """Fetch the HIBP suffixes for a 5-char SHA-1 prefix. Isolated in its own
    function so tests can monkeypatch it (no real network in the suite)."""
    request = urllib.request.Request(
        _HIBP_RANGE_URL + prefix,
        headers={"User-Agent": "FamilyHub-password-check"})
    with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as resp:
        return resp.read().decode("utf-8")


def is_breached(password):
    """True if ``password`` is known-breached per HIBP (k-anonymity). Fails OPEN
    (returns False) on any network/parse error — never blocks on an outage."""
    digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = digest[:5], digest[5:]
    try:
        body = _fetch_hibp_range(prefix)
    except Exception:
        return False
    for line in body.splitlines():
        found_suffix, _sep, _count = line.partition(":")
        if found_suffix.strip().upper() == suffix:
            return True
    return False


def validate_password(password):
    """Enforce the live password baseline. Raises ValueError with a friendly
    message on the first failure; returns None if the password is acceptable.

    This is the ONE gate every password-set path calls (create, admin reset,
    self-service change, token reset) so the rule can't be bypassed by using a
    different entry point."""
    cfg = settings_service.security_config()
    minimum = cfg["min_password_length"]
    if password is None or len(password) < minimum:
        raise ValueError(f"Passwords need at least {minimum} characters.")
    if cfg["breach_check_enabled"] and is_breached(password):
        raise ValueError(
            "That password has appeared in a known data breach — please choose "
            "a different one.")
