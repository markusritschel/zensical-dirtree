"""Render Markdown directly and assert on the HTML — no site build involved."""

from __future__ import annotations

import re
import textwrap

import pytest
from markdown import Markdown
from pymdownx.superfences import SuperFencesException

from zensical_dirtree import DirtreeError

BADGES = {
    "committed": {"label": "committed", "color": "green"},
    "custom": {"label": "custom", "color": "#123abc"},
}


def make_md(
    *, toc: bool = False, superfences: bool = True, anchors: bool = False, **config
) -> Markdown:
    config.setdefault("badges", BADGES)
    extensions = ["pymdownx.highlight", "zensical_dirtree"]
    if superfences:
        extensions.insert(0, "pymdownx.superfences")
    if toc:
        extensions.append("toc")
    configs = {"zensical_dirtree": config}
    if anchors:
        configs["pymdownx.highlight"] = {"anchor_linenums": True}
    return Markdown(extensions=extensions, extension_configs=configs)


def render(source: str, **options) -> str:
    return make_md(**options).convert(source)


def tree(yaml: str) -> str:
    return "````dirtree\n" + textwrap.dedent(yaml).strip("\n") + "\n````\n"


@pytest.fixture(autouse=True)
def project(tmp_path, monkeypatch):
    """Outside Zensical, the project root is the working directory."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "snippets").mkdir()
    return tmp_path


# -- structure ---------------------------------------------------------------


def test_basic_structure():
    html = render(
        tree(
            """
            root: proj/
            nodes:
              - label: config.toml
                summary: Main *configuration*
            """
        )
    )
    assert 'class="dirtree" data-dirtree' in html
    assert 'role="tree"' in html
    assert 'aria-label="proj/"' in html
    assert 'data-node="config-toml"' in html
    assert 'href="#dirtree-config-toml"' in html
    assert 'id="dirtree-config-toml"' in html
    assert 'data-panel="config-toml"' in html
    assert "Main <em>configuration</em>" in html
    # Rendered by us, not left behind as a code block.
    assert "<code>" not in html


def test_nesting_and_folders():
    html = render(
        tree(
            """
            nodes:
              - label: src/
                expanded: true
                children:
                  - label: pkg/
                    children:
                      - label: main.py
              - label: docs
                children: []
              - label: empty/
            """
        )
    )
    assert re.search(r'aria-expanded="true"[^>]*data-node="src"', html)
    assert re.search(r'aria-expanded="false"[^>]*data-node="src-pkg"', html)
    # Folder by `children` key, and folder by trailing slash.
    assert re.search(r'aria-expanded="false"[^>]*data-node="docs"', html)
    assert re.search(r'aria-expanded="false"[^>]*data-node="empty"', html)
    # main.py sits inside pkg's group, which sits inside src's.
    nav = html[: html.index("dirtree__panels")]
    assert re.search(
        r'data-node="src".*?<ul role="group">.*?data-node="src-pkg".*?'
        r'<ul role="group">.*?data-node="src-pkg-main-py"',
        nav,
        re.S,
    )
    # Files carry no aria-expanded.
    assert re.search(r'<li role="treeitem" data-node="src-pkg-main-py"', html)


def test_folder_panel_lists_contents():
    html = render(
        tree(
            """
            nodes:
              - label: src/
                children:
                  - label: a.py
                    summary: The A module
            """
        )
    )
    panel = html[html.index('id="dirtree-src"') :]
    assert "Contents" in panel
    assert 'href="#dirtree-src-a-py"' in panel
    assert "The A module" in panel


def test_breadcrumb_links_ancestors():
    html = render(
        tree(
            """
            root: proj/
            nodes:
              - label: src/
                children:
                  - label: a.py
            """
        )
    )
    panel = html[html.index('id="dirtree-src-a-py"') :]
    crumbs = re.search(r'<p class="dirtree__crumbs">(.*?)</p>', panel).group(1)
    assert 'href="#dirtree-src"' in crumbs
    # Reads as a plain path, current node included, no doubled slashes.
    assert re.sub(r"<[^>]+>", "", crumbs).strip() == "proj / src / a.py"
    assert '<span class="dirtree__crumb-current">a.py</span>' in crumbs


def test_breadcrumb_without_root():
    html = render(tree("nodes:\n  - label: a.py\n"))
    panel = html[html.index('id="dirtree-a-py"') :]
    crumbs = re.search(r'<p class="dirtree__crumbs">(.*?)</p>', panel).group(1)
    assert re.sub(r"<[^>]+>", "", crumbs).strip() == "a.py"


# -- ids ---------------------------------------------------------------------


def test_explicit_id():
    html = render(tree("nodes:\n  - label: a.txt\n    id: custom-id\n"))
    assert 'id="dirtree-custom-id"' in html


def test_auto_id_collision_gets_suffix():
    html = render(tree("nodes:\n  - label: a.b\n  - label: a-b\n"))
    assert 'data-node="a-b"' in html
    assert 'data-node="a-b-2"' in html


def test_auto_id_avoids_explicit_id_declared_later():
    html = render(tree("nodes:\n  - label: a.b\n  - label: other\n    id: a-b\n"))
    assert re.search(r'data-node="a-b-2"[^>]*>.*?a\.b', html, re.S)
    assert html.count('data-node="a-b"') == 1


def test_duplicate_explicit_id_is_error():
    with pytest.raises(DirtreeError, match="duplicate id 'x'"):
        render(tree("nodes:\n  - label: a\n    id: x\n  - label: b\n    id: x\n"))


def test_ids_unique_across_two_trees_on_one_page():
    one = tree("nodes:\n  - label: a.txt\n")
    html = render(one + "\n" + one)
    assert 'id="dirtree-a-txt"' in html
    assert 'id="dirtree-a-txt-2"' in html


def test_ids_reset_between_pages():
    md = make_md()
    md.convert(tree("nodes:\n  - label: a.txt\n"))
    md.reset()
    assert 'id="dirtree-a-txt"' in md.convert(tree("nodes:\n  - label: a.txt\n"))


def test_selected_defaults_to_first_node():
    html = render(tree("nodes:\n  - label: a\n  - label: b\n"))
    assert 'data-selected="a"' in html


def test_selected_explicit_and_unknown():
    html = render(tree("selected: b\nnodes:\n  - label: a\n  - label: b\n"))
    assert 'data-selected="b"' in html
    with pytest.raises(DirtreeError, match="selected"):
        render(tree("selected: nope\nnodes:\n  - label: a\n"))


# -- badges and fields -------------------------------------------------------


def test_named_badge():
    html = render(tree("nodes:\n  - label: a\n    badges: [committed]\n"))
    assert 'class="dirtree__badge dirtree__badge--green"' in html
    assert ">committed</span>" in html


def test_raw_colour_badge():
    html = render(tree("nodes:\n  - label: a\n    badges: [custom]\n"))
    assert 'style="--dirtree-badge: #123abc"' in html


def test_badge_defaults_label_to_key():
    html = render(
        tree("nodes:\n  - label: a\n    badges: [x]\n"),
        badges={"x": {"color": "blue"}},
    )
    assert ">x</span>" in html


def test_unknown_badge_is_error():
    with pytest.raises(DirtreeError, match="unknown badge 'nope'"):
        render(tree("nodes:\n  - label: a\n    badges: [nope]\n"))


def test_unsafe_badge_colour_is_error():
    with pytest.raises(DirtreeError, match="colour"):
        render(
            tree("nodes:\n  - label: a\n    badges: [x]\n"),
            badges={"x": {"color": 'red" onmouseover="alert(1)'}},
        )


def test_fields_render_inline_markdown():
    html = render(
        tree(
            """
            nodes:
              - label: a
                fields:
                  - label: Read when
                    value: At `startup`
            """
        )
    )
    assert "<dt>Read when</dt>" in html
    assert "<dd>At <code>startup</code></dd>" in html


def test_malformed_field_is_error():
    with pytest.raises(DirtreeError, match="fields"):
        render(tree("nodes:\n  - label: a\n    fields: [oops]\n"))


def test_link():
    html = render(tree("nodes:\n  - label: a\n    link: /reference/\n"))
    assert '<a href="/reference/">Full docs' in html


# -- bodies ------------------------------------------------------------------


def test_body_markdown_and_code_fence():
    html = render(
        tree(
            """
            nodes:
              - label: a
                body: |
                  Some **bold** text.

                  ```toml
                  port = 8080
                  ```
            """
        )
    )
    body = html[html.index("dirtree__body") :]
    assert "<strong>bold</strong>" in body
    assert '<div class="highlight">' in body


def test_body_code_renders_like_page_code():
    fence = "```toml\nport = 8080\n```\n"
    page = render(fence)
    html = render(
        tree(
            "nodes:\n  - label: a\n    body: |\n      "
            + fence.replace("\n", "\n      ")
        )
    )
    assert page.strip() in html


def test_code_line_ids_do_not_collide_with_page():
    body_tree = tree(
        """
        nodes:
          - label: a
            body: |
              ```python
              y = 2
              ```
        """
    )
    source = "```python\nx = 1\n```\n\n" + body_tree + "\n```python\nz = 3\n```\n"
    html = render(source, anchors=True)
    ids = re.findall(r'id="(__codelineno-[^"]+)"', html)
    assert len(ids) == 3, html
    assert len(set(ids)) == 3, ids


def test_body_file(project):
    (project / "snippets" / "main.md").write_text("From *file*.\n")
    html = render(
        tree("nodes:\n  - label: main.py\n    body_file: main.md\n"),
        base_path="snippets",
    )
    assert "From <em>file</em>." in html


def test_body_and_body_file_is_error():
    source = tree(
        """
        nodes:
          - label: src/
            children:
              - label: a
                body: x
                body_file: a.md
        """
    )
    with pytest.raises(DirtreeError, match=r"node 'src/a'.*both 'body' and"):
        render(source)


def test_missing_body_file_is_error(project):
    with pytest.raises(DirtreeError) as info:
        render(
            tree("nodes:\n  - label: a\n    body_file: nope.md\n"),
            base_path="snippets",
        )
    message = str(info.value)
    assert "node 'a'" in message
    assert str(project / "snippets" / "nope.md") in message


def test_body_file_traversal_is_error(project):
    (project.parent / "secret.md").write_text("nope")
    with pytest.raises(DirtreeError, match="outside the project root"):
        render(
            tree("nodes:\n  - label: a\n    body_file: ../../secret.md\n"),
            base_path="snippets",
        )


def test_base_path_traversal_is_error():
    with pytest.raises(DirtreeError, match="outside the project root"):
        render(tree("nodes:\n  - label: a\n    body_file: x.md\n"), base_path="..")


# -- escaping, TOC, validation ----------------------------------------------


def test_labels_are_escaped():
    html = render(
        tree(
            """
            root: "<b>root</b>"
            nodes:
              - label: "<script>alert(1)</script>"
            """
        )
    )
    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<b>root</b>" not in html


def test_panels_do_not_pollute_toc():
    md = make_md(toc=True)
    md.convert(
        "# Page\n\n"
        + tree(
            """
            nodes:
              - label: a
                body: |
                  ## Inside body
            """
        )
    )
    assert [t["name"] for t in md.toc_tokens] == ["Page"]
    assert md.toc_tokens[0]["children"] == []


def test_icons():
    html = render(
        tree(
            """
            nodes:
              - label: src/
              - label: main.py
              - label: config.toml
              - label: README.md
              - label: LICENSE
              - label: special
                icon: code
            """
        )
    )
    nav = html[: html.index("dirtree__panels")]
    for node, icon in [
        ("src", "folder"),
        ("main-py", "code"),
        ("config-toml", "config"),
        ("readme-md", "md"),
        ("license", "file"),
        ("special", "code"),
    ]:
        assert re.search(
            rf'data-node="{node}"[^>]*>.*?dirtree__icon--{icon}"', nav, re.S
        ), node


def test_invalid_icon_is_error():
    with pytest.raises(DirtreeError, match="icon"):
        render(tree("nodes:\n  - label: a\n    icon: rocket\n"))


@pytest.mark.parametrize(
    ("yaml", "match"),
    [
        ("nodes: [", "invalid YAML"),
        ("root: x\n", "'nodes'"),
        ("nodes: []\n", "'nodes'"),
        ("nodes:\n  - just a string\n", "mapping"),
        ("nodes:\n  - summary: no label\n", "label"),
        ("nodes:\n  - label: a\n    colour: red\n", "unknown key 'colour'"),
        ("nodes:\n  - label: a\n    children: nope\n", "children"),
        ("nodes:\n  - label: a\nextra: 1\n", "unknown key 'extra'"),
    ],
)
def test_validation_errors(yaml, match):
    with pytest.raises(DirtreeError, match=match):
        render(tree(yaml))


def test_errors_propagate_through_superfences():
    # SuperFences swallows ordinary formatter exceptions and emits a plain code
    # block; ours must survive that to fail the build.
    assert issubclass(DirtreeError, SuperFencesException)


def test_missing_superfences_is_error():
    with pytest.raises(DirtreeError, match="pymdownx.superfences"):
        render(tree("nodes:\n  - label: a\n"), superfences=False)


def test_missing_superfences_ignored_without_dirtree_fence():
    assert "<p>hello</p>" in render("hello", superfences=False)


def test_error_names_page_outside_zensical():
    with pytest.raises(DirtreeError, match=r"^dirtree: <page>: "):
        render(tree("nodes:\n  - label: a\n    icon: rocket\n"))
