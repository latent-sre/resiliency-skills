"""Malicious-fixture test pinned to the redact rules (review item F12).

Fake secrets are ASSEMBLED at runtime (concatenation / random) so no secret-shaped literal is
committed to this repo — keeping the repo's own secret scanners quiet while still exercising the
detector with realistic inputs.
"""
import base64
import os

from latent_sre import redact


def _findings(text: str):
    return redact.scan_text(text, "<test>")


def test_blocks_known_patterns():
    aws = "AKIA" + "I" * 16
    gh = "ghp_" + "x" * 36
    jwt = "eyJ" + "a" * 6 + ".eyJ" + "b" * 6 + ".sig123"
    pem = "-----BEGIN RSA PRIVATE KEY-----"
    uri = "postgres://user:" + "p" * 12 + "@db.internal:5432/app"
    for secret in (aws, gh, jwt, pem, uri):
        assert _findings(f"value: {secret}"), f"should have flagged: {secret[:6]}…"


def test_blocks_high_entropy():
    # urlsafe base64 (charset A-Za-z0-9-_) so the opaque token has no '/' or '.' separators.
    token = base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")
    assert any(f.rule == "high-entropy" for f in _findings(f"opaque: {token}"))


def test_blocks_value_shape():
    findings = _findings("db_password: s3cretValueWithLength")
    assert any(f.rule in ("value-shape", "high-entropy") for f in findings)


def test_clean_text_passes():
    clean = (
        "apiVersion: sre.latent-sre/v1\n"
        "kind: Criticality\n"
        "service: checkout\n"
        "tier: tier1\n"
        "ownership: app\n"
        "needs-human-review: true\n"
    )
    assert _findings(clean) == []


def test_sentinel_is_allowed():
    assert _findings("index: REPLACE_ME__splunk_index") == []


def test_inline_allow_suppresses():
    secret = "AKIA" + "Z" * 16
    assert _findings(f"value: {secret}  # latent-sre:allow known test fixture") == []


def test_findings_never_echo_full_secret():
    secret = "ghp_" + "y" * 36
    out = str(_findings(f"token: {secret}")[0])
    assert secret not in out  # only a redacted excerpt is shown


def test_allowlist_ignores_indented_comments(tmp_path):
    # Indented `# ...` lines must be treated as comments, not as literal allow-substrings (which
    # could silently suppress real findings on any line containing that text).
    (tmp_path / redact.ALLOW_FILE).write_text(
        "realstring\n  # indented comment\n# top comment\n", encoding="utf-8")
    assert redact._load_allowlist(tmp_path) == ["realstring"]


def test_known_pattern_reports_every_match_on_a_line():
    a = "AKIA" + "A" * 16
    b = "AKIA" + "B" * 16
    aws = [f for f in _findings(f"keys: {a} and {b}") if f.rule == "aws-access-key-id"]
    assert len(aws) == 2  # both keys flagged, not just the first match
