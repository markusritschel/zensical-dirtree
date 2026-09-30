"""Interactive directory-tree explorer for Zensical pages."""

from __future__ import annotations

from pathlib import Path

from zensical_dirtree.extension import DirtreeError, DirtreeExtension, makeExtension

__all__ = ["ASSETS", "DirtreeError", "DirtreeExtension", "asset_path", "makeExtension"]
__version__ = "0.1.0"

#: Bundled assets, in the order they should be registered.
ASSETS = ("dirtree.css", "dirtree.js")


def asset_path(name: str) -> Path:
    """Return the on-disk path of a bundled asset."""
    if name not in ASSETS:
        raise ValueError(f"unknown asset {name!r}; expected one of {ASSETS}")
    return Path(__file__).parent / "assets" / name
