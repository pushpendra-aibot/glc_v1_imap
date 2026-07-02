"""RFC 8601 Authentication-Results header parser.

Answers one question: did the receiving mail server certify that the
message's From: address is authentic?

Why we trust the receiving MTA's verdict instead of verifying ourselves
-----------------------------------------------------------------------
SPF/DKIM/DMARC verification requires DNS access plus ~500 lines of
cryptographic machinery (dkimpy, dnspython, etc.). The receiving MTA
(Zoho, Gmail, Fastmail, …) already ran all three checks before
delivering the message and stamped the outcome in Authentication-Results:.
We read that stamp — zero new dependencies, zero DNS calls.

Anti-forgery: header order matters
-----------------------------------
An attacker can inject a fake Authentication-Results: header inside
the body of their spoofed email. The receiving MTA *prepends* its own
copy above any attacker-supplied content. Therefore we iterate headers
in order and select the first one whose authserv-id matches a
caller-supplied trusted set. An injected copy with a foreign
authserv-id is simply skipped.

If no trusted copy is found the verdict is 'missing', which the caller
treats as a failed check.

Public API
----------
    parse_authentication_results(raw_headers, trusted_authserv_ids)
        -> AuthVerdict

    auth_passes(verdict, from_address)
        -> bool   (True iff the From: address is cryptographically
                   backed by a pass verdict from a trusted MTA)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Literal

log = logging.getLogger(__name__)

# Valid result tokens per RFC 8601 §2.7.1 plus 'missing' (our sentinel).
AuthResult = Literal[
    "pass", "fail", "softfail", "neutral", "none",
    "temperror", "permerror", "missing",
]

# Regex for the leading "authserv-id" token before the first ";".
# authserv-id is a hostname or domain, tolerant of sub-domains and ports.
_AUTHSERV_RE = re.compile(r"^\s*([A-Za-z0-9][\w.\-]*)")

# Regex to find   method=result   tokens anywhere in the header value.
# We allow optional spaces around "=" and stop at the next ";" or end.
# Comments (...) are stripped before matching.
_METHOD_RE = re.compile(
    r"\b(spf|dkim|dmarc)\s*=\s*"
    r"(pass|fail|softfail|neutral|none|temperror|permerror)",
    re.IGNORECASE,
)

# Regex for property tags: header.d=, header.from=, smtp.mailfrom=, etc.
_PROP_RE = re.compile(
    r"\b(header\.(?:d|i|from)|smtp\.mailfrom)\s*=\s*([\w.\-@]+)",
    re.IGNORECASE,
)

# Inline RFC 5322 comment stripper: removes  (any text)  pairs.
_COMMENT_RE = re.compile(r"\([^)]*\)")


@dataclass
class AuthVerdict:
    """Parsed result from an Authentication-Results: header.

    All three verdict fields default to 'missing', meaning the header
    was absent or no trusted authserv-id was found.
    """

    spf: AuthResult = "missing"
    dkim: AuthResult = "missing"
    dmarc: AuthResult = "missing"

    # Domains extracted from property tags inside the header.
    dkim_domain: str = ""   # header.d= or header.i= (rightmost label)
    spf_domain: str = ""    # smtp.mailfrom= (rightmost label)
    from_header_domain: str = ""  # header.from=

    # True when at least one of DKIM/SPF authenticated a domain that
    # matches the visible From: domain.
    from_aligned: bool = False

    authserv_id: str | None = None   # which MTA produced this verdict
    raw: str | None = None           # full header value for debugging

    _trusted_match: bool = field(default=False, repr=False)


def _domain(addr: str) -> str:
    """Return the lowercase domain part of an email address or domain string.

    'user@Example.COM' -> 'example.com'
    'Example.COM'      -> 'example.com'
    ''                 -> ''
    """
    addr = addr.strip().lower()
    if "@" in addr:
        addr = addr.split("@", 1)[1]
    return addr


def _strip_comments(value: str) -> str:
    return _COMMENT_RE.sub(" ", value)


def _parse_one(header_value: str, from_domain: str) -> AuthVerdict:
    """Parse a single Authentication-Results: header value string."""
    clean = _strip_comments(header_value)

    # Extract authserv-id (everything before the first ";").
    parts = clean.split(";", 1)
    authserv_id_raw = parts[0].strip()
    m = _AUTHSERV_RE.match(authserv_id_raw)
    authserv_id = m.group(1).lower() if m else ""

    body = parts[1] if len(parts) > 1 else ""

    # Parse method=result pairs.
    results: dict[str, str] = {}
    for match in _METHOD_RE.finditer(body):
        method = match.group(1).lower()
        result = match.group(2).lower()
        if method not in results:   # first occurrence wins
            results[method] = result

    spf: AuthResult = results.get("spf", "missing")  # type: ignore[assignment]
    dkim: AuthResult = results.get("dkim", "missing")  # type: ignore[assignment]
    dmarc: AuthResult = results.get("dmarc", "missing")  # type: ignore[assignment]

    # Parse property tags for alignment data.
    props: dict[str, str] = {}
    for match in _PROP_RE.finditer(body):
        key = match.group(1).lower()
        val = match.group(2).strip()
        if key not in props:
            props[key] = val

    dkim_domain = _domain(props.get("header.d", props.get("header.i", "")))
    spf_domain = _domain(props.get("smtp.mailfrom", ""))
    from_header_domain = _domain(props.get("header.from", ""))

    # Alignment: does any authenticated domain match the visible From: domain?
    from_aligned = False
    if from_domain:
        if dkim == "pass" and dkim_domain and dkim_domain == from_domain:
            from_aligned = True
        if spf == "pass" and spf_domain and spf_domain == from_domain:
            from_aligned = True
        if from_header_domain and from_header_domain == from_domain:
            # header.from= in the AR header itself being aligned is
            # informational; pair it with at least one passing method.
            if dkim == "pass" or spf == "pass":
                from_aligned = True

    return AuthVerdict(
        spf=spf,
        dkim=dkim,
        dmarc=dmarc,
        dkim_domain=dkim_domain,
        spf_domain=spf_domain,
        from_header_domain=from_header_domain,
        from_aligned=from_aligned,
        authserv_id=authserv_id,
        raw=header_value,
    )


def parse_authentication_results(
    raw_headers: list[str],
    trusted_authserv_ids: set[str],
) -> AuthVerdict:
    """Select and parse the first trusted Authentication-Results: header.

    Parameters
    ----------
    raw_headers:
        All values of the Authentication-Results: header, in the order
        the MUA/parser returned them (i.e. top-of-message first).
        Obtain via ``msg.get_all("Authentication-Results") or []``.
    trusted_authserv_ids:
        Set of lowercase authserv-id strings to trust, e.g.
        ``{"mx.google.com", "zoho.in"}``.  The caller controls this set
        to prevent attacker-injected headers from being trusted.

    Returns
    -------
    AuthVerdict
        The first verdict from a trusted MTA, or a fully-missing verdict
        if none is found.
    """
    missing = AuthVerdict()

    if not trusted_authserv_ids:
        log.debug("[auth ] No trusted_authserv_ids configured — all verdicts missing")
        return missing

    for raw in raw_headers:
        try:
            verdict = _parse_one(raw, from_domain="")  # domain filled in later
            if verdict.authserv_id in trusted_authserv_ids:
                log.debug(
                    "[auth ] Trusted AR header from %s: dmarc=%s dkim=%s spf=%s",
                    verdict.authserv_id, verdict.dmarc, verdict.dkim, verdict.spf,
                )
                return verdict
        except Exception:
            log.warning("[auth ] Failed to parse Authentication-Results header", exc_info=True)
            continue

    log.debug("[auth ] No trusted Authentication-Results header found in %d headers", len(raw_headers))
    return missing


def auth_passes(verdict: AuthVerdict, from_address: str) -> bool:
    """Return True iff the verdict is sufficient to trust the From: address.

    Policy (mirrors RFC 7489 §4.2):
      - DMARC pass is always sufficient (it already enforces alignment).
      - Without DMARC: DKIM pass + From: domain alignment is sufficient.
      - SPF pass alone is insufficient (SPF checks envelope-from, not
        header-from; a DMARC-aligned SPF pass requires the same domain,
        and that is only guaranteed when dmarc=pass).
      - Any 'missing' verdict ⇒ False (fail-closed).
    """
    if verdict.dmarc == "missing" and verdict.dkim == "missing":
        return False

    if verdict.dmarc == "pass":
        return True

    # DMARC absent/fail — fall back to DKIM alignment.
    if verdict.dkim == "pass":
        from_domain = _domain(from_address)
        # Re-compute alignment now that we have the actual from_address.
        if from_domain and verdict.dkim_domain and verdict.dkim_domain == from_domain:
            return True

    return False
