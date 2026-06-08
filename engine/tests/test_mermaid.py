"""Mermaid dependency graph: untrusted-label sanitization + unique node ids."""
import re

from latent_sre import mermaid


def _write(tmp_path, doc: str):
    p = tmp_path / "dependencies.yaml"
    p.write_text(doc, encoding="utf-8")
    return p


def test_basic_graph_has_service_and_edges(tmp_path):
    out = mermaid.from_dependencies(_write(tmp_path,
        "service: checkout\ndependencies:\n  - {name: redis, direction: downstream}\n"))
    assert out.startswith("```mermaid") and out.rstrip().endswith("```")
    assert "n_checkout[checkout]" in out
    assert "--> n_redis[redis]" in out


def test_distinct_names_that_sanitize_alike_get_distinct_nodes(tmp_path):
    # `redis.cache` and `redis-cache` both sanitize to n_redis_cache; they must NOT merge into one node.
    out = mermaid.from_dependencies(_write(tmp_path,
        "service: s\ndependencies:\n"
        "  - {name: redis.cache, direction: downstream}\n"
        "  - {name: redis-cache, direction: upstream}\n"))
    node_ids = re.findall(r"(n_\S+?)\[", out)
    dep_ids = [i for i in node_ids if i != "n_s"]
    assert len(dep_ids) == len(set(dep_ids)) == 2  # two unique target nodes, not one collapsed node


def test_repeated_name_reuses_the_same_node(tmp_path):
    # The same dependency referenced twice should connect to a single node (one id reused).
    out = mermaid.from_dependencies(_write(tmp_path,
        "service: s\ndependencies:\n"
        "  - {name: db, direction: downstream}\n"
        "  - {name: db, direction: upstream}\n"))
    assert out.count("n_db[db]") == 2 and len(set(re.findall(r"n_db\b", out))) == 1
