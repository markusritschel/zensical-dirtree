"""Command-line helpers for zensical-dirtree.

The extension inlines its stylesheet and script by default. Sites that set
``inline_assets = false`` copy them into the docs directory like any other
custom asset instead. The JSON Schema for tree files is copied out for editors
to pick up:

    zensical-dirtree install [--docs-dir docs]
    zensical-dirtree schema [--output snippets/trees/dirtree.schema.json]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from zensical_dirtree import ASSETS, SCHEMA_PATH, asset_path

#: Conventional locations, matching the theme's own documentation.
SUBDIRS = {".css": "stylesheets", ".js": "javascripts"}


def install(docs_dir: Path) -> int:
    if not docs_dir.is_dir():
        print(f"No such directory: {docs_dir.resolve()}", file=sys.stderr)
        print("Pass your docs directory, e.g. --docs-dir docs", file=sys.stderr)
        return 1

    for name in ASSETS:
        target = docs_dir / SUBDIRS[Path(name).suffix] / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(asset_path(name), target)
        print(f"Wrote {target}")

    print(
        "\nNow add to zensical.toml:\n\n"
        "  [project]\n"
        '  extra_css = ["stylesheets/dirtree.css"]\n'
        '  extra_javascript = ["javascripts/dirtree.js"]\n'
        '  watch = ["snippets"]   # your base_path, so body edits rebuild\n\n'
        "  [project.markdown_extensions.zensical_dirtree]\n"
        '  base_path = "snippets"\n'
        "  inline_assets = false\n"
    )
    return 0


def schema(output: Path | None) -> int:
    if output is None:
        sys.stdout.write(SCHEMA_PATH.read_text(encoding="utf-8"))
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SCHEMA_PATH, output)
    print(f"Wrote {output}")
    print(
        "\nReference it from the first line of a tree file, relative to that file:"
        f"\n\n  # yaml-language-server: $schema={output.name}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zensical-dirtree",
        description="Utilities for the zensical-dirtree Markdown extension.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    installer = sub.add_parser("install", help="copy assets into a docs directory")
    installer.add_argument(
        "--docs-dir",
        default="docs",
        type=Path,
        help="path to the docs directory (default: docs)",
    )
    schemer = sub.add_parser(
        "schema", help="print or write the JSON Schema for tree files"
    )
    schemer.add_argument(
        "--output",
        type=Path,
        help="write the schema to this file instead of printing it",
    )
    args = parser.parse_args(argv)
    if args.command == "schema":
        return schema(args.output)
    return install(args.docs_dir)


if __name__ == "__main__":
    raise SystemExit(main())
