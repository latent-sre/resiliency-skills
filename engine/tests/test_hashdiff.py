"""Normalized content hashing: cosmetic reformatting / volatile fields don't read as a human edit."""
from latent_sre import hashdiff


def test_json_hash_invariant_to_key_order_and_whitespace(tmp_path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text('{"x": 1, "y": 2}', encoding="utf-8")
    b.write_text('{\n  "y": 2,\n  "x": 1\n}', encoding="utf-8")
    assert hashdiff.content_hash(a) == hashdiff.content_hash(b)


def test_json_hash_strips_volatile_fields(tmp_path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text('{"k": 1, "scanDate": "2026-01-01"}', encoding="utf-8")
    b.write_text('{"k": 1, "scanDate": "2030-12-31"}', encoding="utf-8")
    assert hashdiff.content_hash(a) == hashdiff.content_hash(b)  # scanDate is volatile


def test_json_hash_detects_real_change(tmp_path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text('{"k": 1}', encoding="utf-8")
    b.write_text('{"k": 2}', encoding="utf-8")
    assert hashdiff.content_hash(a) != hashdiff.content_hash(b)
