"""Fail-closed secret/PII gate (review item F12).

This is the single load-bearing safety control. It must BLOCK (non-zero exit) on any plausible
secret/credential rather than emit best-effort. Detection rules, kept in sync with the
malicious-fixture test (``tests/test_redact.py``):

1. Known-pattern set   — cloud keys, VCS/chat tokens, JWTs, PEM private keys, connection strings.
2. High entropy        — Shannon entropy >= 4.0 bits/char over a token of length >= 20.
3. Value-shape         — ``<secretish-key>: <opaque-value>`` where the key name looks secret-ish.

Escape hatch (manage false positives without disabling the gate):
* an inline ``# latent-sre:allow <reason>`` comment on the same line, or
* a checked-in ``.latent-sre-allow`` file listing literal substrings to ignore (one per line).

Placeholder sentinels emitted by ``render-adapters`` (``REPLACE_ME__...``) are never findings.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

ENTROPY_MIN_BITS = 4.0
ENTROPY_MIN_LEN = 20
ALLOW_INLINE = "# latent-sre:allow"
ALLOW_FILE = ".latent-sre-allow"
SENTINEL_PREFIX = "REPLACE_ME__"

# 1. Known patterns. Each is (name, compiled regex). Kept deliberately specific to limit noise.
KNOWN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws-access-key-id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bgh[posru]_[0-9A-Za-z]{36,}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("jwt", re.compile(r"\beyJ[0-9A-Za-z_\-]+\.eyJ[0-9A-Za-z_\-]+\.[0-9A-Za-z_\-]+\b")),
    ("private-key-block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("bearer-token", re.compile(r"\bBearer\s+[0-9A-Za-z._\-]{20,}\b")),
    # scheme://user:password@host  — credentials embedded in a connection URI
    ("uri-with-credentials", re.compile(r"\b[a-z][a-z0-9+.\-]*://[^\s:/@]+:[^\s:/@]+@[^\s/]+", re.I)),
]

# 3. Value-shape: keys whose value should never be a real literal in a published artifact.
# Match on normalized key segments (handles db_password, accessKey, client-secret, …) rather than
# word boundaries, which don't fire across underscores.
SECRETISH_MARKERS = (
    "password", "passwd", "pwd", "secret", "token", "apikey", "accesskey",
    "privatekey", "clientsecret", "credential", "connectionstring", "connstring", "dsn",
)


def _is_secretish_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", key.lower())
    return any(marker in normalized for marker in SECRETISH_MARKERS)
# A value that "looks like" an opaque secret (not a placeholder / boolean / short word).
OPAQUE_VALUE = re.compile(r"""^['"]?[^\s'"]{12,}['"]?$""")
PLACEHOLDERISH = re.compile(r"(?i)(\$\{|<|changeme|example|placeholder|xxx|todo|none|null|true|false)")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    excerpt: str

    def __str__(self) -> str:  # short, never echoes the full secret
        return f"{self.path}:{self.line} [{self.rule}] {self.excerpt}"


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts: dict[str, int] = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _redacted(token: str) -> str:
    """Never print a full secret in findings output."""
    if len(token) <= 8:
        return "***"
    return f"{token[:3]}…{token[-2:]} (len {len(token)})"


def _load_allowlist(root: Path) -> list[str]:
    f = root / ALLOW_FILE
    if not f.is_file():
        return []
    # Strip first, then test for a comment — so indented `# ...` lines are treated as comments,
    # not as literal allow-substrings that could silently suppress real findings.
    return [s for ln in f.read_text().splitlines() if (s := ln.strip()) and not s.startswith("#")]


_TOKEN_RE = re.compile(r"[^\s'\"=:,;()\[\]{}<>]+")
# Opaque secret charset (base64/base64url/hex). Note '.' and '/' are deliberately excluded so paths,
# URLs, filenames and hostnames are NOT treated as high-entropy secrets (a common false-positive).
_OPAQUE = re.compile(r"^[A-Za-z0-9+=_-]+$")


def _entropy_candidate(tok: str) -> bool:
    if tok.startswith(SENTINEL_PREFIX) or len(tok) < ENTROPY_MIN_LEN:
        return False
    if not _OPAQUE.match(tok):  # contains '/', '.', or other structure → not an opaque secret
        return False
    return any(c.isdigit() for c in tok) and any(c.isalpha() for c in tok)


def scan_text(text: str, path: str = "<text>", allow: list[str] | None = None) -> list[Finding]:
    allow = allow or []
    findings: list[Finding] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if ALLOW_INLINE in line:
            continue
        if any(a and a in line for a in allow):
            continue

        # 1. Known patterns — report every match on the line, not just the first.
        for name, pat in KNOWN_PATTERNS:
            for m in pat.finditer(line):
                findings.append(Finding(path, i, name, _redacted(m.group(0))))

        # 2. High-entropy opaque tokens (paths/URLs/filenames excluded via _entropy_candidate)
        for tok in _TOKEN_RE.findall(line):
            if _entropy_candidate(tok) and shannon_entropy(tok) >= ENTROPY_MIN_BITS:
                findings.append(Finding(path, i, "high-entropy", _redacted(tok)))

        # 3. Value-shape
        if ":" in line:
            key, _, value = line.partition(":")
            value = value.strip()
            if (
                _is_secretish_key(key)
                and value
                and not value.startswith(SENTINEL_PREFIX)
                and OPAQUE_VALUE.match(value)
                and not PLACEHOLDERISH.search(value)
            ):
                findings.append(Finding(path, i, "value-shape", f"{key.strip()}: {_redacted(value)}"))

    # de-duplicate (a line can trip multiple rules on the same token)
    seen: set[tuple] = set()
    unique: list[Finding] = []
    for f in findings:
        k = (f.path, f.line, f.rule, f.excerpt)
        if k not in seen:
            seen.add(k)
            unique.append(f)
    return unique


def scan_path(target: Path) -> list[Finding]:
    """Scan a file or directory tree. Fail-closed: callers block publish if this is non-empty."""
    target = Path(target)
    root = target if target.is_dir() else target.parent
    allow = _load_allowlist(root)
    findings: list[Finding] = []
    paths = [target] if target.is_file() else [
        p for p in target.rglob("*") if p.is_file() and ".git" not in p.parts
    ]
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary / unreadable — skip
        findings.extend(scan_text(text, str(p), allow))
    return findings
