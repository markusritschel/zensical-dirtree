"""The shipped JSON Schema must agree with the extension's own validation."""

from __future__ import annotations

import json
import textwrap

import pytest
import yaml
from jsonschema import Draft202012Validator
from markdown import Markdown

from zensical_dirtree import SCHEMA_PATH, DirtreeError
from zensical_dirtree.extension import ICONS, NODE_KEYS, TOP_KEYS

SCHEMA = json.loads(SCHEMA_PATH.read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


def schema_accepts(text: str) -> bool:
    return VALIDATOR.is_valid(yaml.safe_load(textwrap.dedent(text)))


def renderer_accepts(text: str) -> bool:
    md = Markdown(
        extensions=["pymdownx.superfences", "zensical_dirtree"],
        extension_configs={"zensical_dirtree": {"badges": {"ok": {}}}},
    )
    try:
        md.convert("````dirtree\n" + textwrap.dedent(text).strip() + "\n````\n")
    except DirtreeError:
        return False
    return True


def test_schema_is_valid_draft_2020_12():
    Draft202012Validator.check_schema(SCHEMA)


def test_schema_keys_match_the_validator():
    assert set(SCHEMA["properties"]) == TOP_KEYS
    node = SCHEMA["$defs"]["node"]
    assert set(node["properties"]) == NODE_KEYS
    assert set(node["properties"]["icon"]["enum"]) == set(ICONS)


VALID = """
root: proj/
selected: src-main-py
nodes:
  - label: config.toml
    id: config-toml
    summary: Main *configuration*
    badges: [ok]
    fields:
      - label: Read when
        value: At startup
    body: |
      Some text.
    link: reference.md
  - label: src/
    expanded: true
    icon: folder
    children:
      - label: main.py
  - label: 2024
    children:
"""


def test_valid_tree_passes_both():
    assert schema_accepts(VALID)
    assert renderer_accepts(VALID)


@pytest.mark.parametrize(
    "text",
    [
        "root: x\n",  # no nodes
        "nodes: []\n",  # empty nodes
        "nodes:\n  - summary: no label\n",
        "nodes:\n  - label: a\n    colour: red\n",  # unknown node key
        "nodes:\n  - label: a\nextra: 1\n",  # unknown top-level key
        "nodes:\n  - label: a\n    body: x\n    body_file: a.md\n",
        "nodes:\n  - label: a\n    icon: rocket\n",
        "nodes:\n  - label: a\n    id: a.b\n",
        "nodes:\n  - label: a\n    expanded: yes please\n",
        "nodes:\n  - label: a\n    fields: [oops]\n",
        "nodes:\n  - label: a\n    children: nope\n",
        "src: other.yaml\nnodes:\n  - label: a\n",  # src is fence-only
    ],
)
def test_invalid_trees_fail_both(text):
    assert not schema_accepts(text)
    assert not renderer_accepts(text)
