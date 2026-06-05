"""Safe YAML I/O. All target-repo content is untrusted → safe_load only, never yaml.load."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

_yaml = YAML(typ="safe")  # safe loader: no arbitrary object construction
_yaml.default_flow_style = False
_yaml.sort_keys = True  # canonical ordering for normalized hashing (F-determinism)


def load(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return _yaml.load(fh)


def loads(text: str) -> Any:
    return _yaml.load(text)


def dumps(data: Any) -> str:
    buf = io.StringIO()
    _yaml.dump(data, buf)
    return buf.getvalue()


def dump(data: Any, path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        _yaml.dump(data, fh)
