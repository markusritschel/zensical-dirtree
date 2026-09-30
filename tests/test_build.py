"""Real Zensical builds of the example site: the integration the unit tests
cannot see (config-driven registration, nested rendering, error propagation)."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("zensical")

EXAMPLE = Path(__file__).parent.parent / "example"


@pytest.fixture
def site(tmp_path):
    root = tmp_path / "example"
    shutil.copytree(EXAMPLE, root, ignore=shutil.ignore_patterns("site", ".cache"))
    return root


def build(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "zensical", "build", "--clean"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_example_builds(site):
    result = build(site)
    assert result.returncode == 0, result.stdout + result.stderr
    html = (site / "site" / "index.html").read_text()
    assert html.count("data-dirtree ") == 2
    # body_file content, rendered with the site's own highlighter settings.
    assert "create_app" in html
    assert 'class="language-python highlight"' in html
    # A relative link in `link:` is resolved like any page link.
    assert re.search(r'dirtree__more"><a href="reference/"', html)
    ids = re.findall(r'\sid="([^"]+)"', html)
    assert len(ids) == len(set(ids)), "duplicate ids on the page"
    search = (site / "site" / "search.json").read_text()
    assert "Per-machine overrides" in search


def test_invalid_tree_fails_the_build(site):
    page = site / "docs" / "second.md"
    page.write_text(
        page.read_text()
        + "\n````dirtree\nnodes:\n  - label: a\n    icon: rocket\n````\n"
    )
    result = build(site)
    assert result.returncode != 0
    assert "unknown icon 'rocket'" in result.stdout + result.stderr


def test_missing_superfences_fails_the_build(site):
    config = site / "zensical.toml"
    text = config.read_text()
    text = re.sub(
        r"\[project\.markdown_extensions\.pymdownx\.superfences\]\n.*\n", "", text
    )
    config.write_text(text)
    result = build(site)
    assert result.returncode != 0
    assert "needs pymdownx.superfences" in result.stdout + result.stderr
