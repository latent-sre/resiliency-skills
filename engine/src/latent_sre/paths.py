"""Locate bundled data (schemas, adapter templates) in both layouts:

* source / repo checkout — ``engine/<name>`` (next to ``src/``), and
* installed wheel — ``latent_sre/_data/<name>`` (force-included at build time, see pyproject).
"""
from __future__ import annotations

from pathlib import Path


def data_dir(name: str) -> Path:
    repo = Path(__file__).resolve().parents[2] / name      # engine/<name> (source layout)
    if repo.is_dir():
        return repo
    return Path(__file__).resolve().parent / "_data" / name  # installed wheel layout


def data_file(name: str) -> Path:
    repo = Path(__file__).resolve().parents[2] / name        # engine/<name> (source layout)
    if repo.is_file():
        return repo
    return Path(__file__).resolve().parent / "_data" / name  # installed wheel layout
