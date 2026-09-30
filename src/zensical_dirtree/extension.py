"""Python-Markdown extension rendering ``dirtree`` fences as a static explorer.

The fence is a pymdownx.superfences custom fence, registered by this extension
itself: a small preprocessor running just before SuperFences' own (priority 25)
finds the SuperFences instance on the Markdown object and adds the fence. That
works whatever order the extensions are listed in, so users configure nothing
but this extension.

Node bodies go through a nested Markdown instance. Under Zensical it is built
from the site's own configuration, so bodies get exactly the page's pipeline;
elsewhere (unit tests, plain Python-Markdown) a standard set is used.

Errors subclass ``SuperFencesException``: SuperFences swallows any other
exception raised by a formatter and silently emits a plain code block instead.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any

import yaml
from markdown import Markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
from pymdownx.superfences import SuperFencesException

log = logging.getLogger("zensical_dirtree")

FENCE = "dirtree"
PREFIX = "dirtree-"

#: Just above SuperFences' ``fenced_code_block`` preprocessor (25).
REGISTER_PRIORITY = 27

FENCE_RE = re.compile(rf"^\s*(`{{3,}}|~{{3,}})\s*{FENCE}\s*$")
ID_RE = re.compile(r"^[\w-]+$")
#: Loose allow-list for raw CSS colours: enough for hex, names and functions,
#: nothing that could leave the style attribute.
COLOUR_RE = re.compile(r"^[#\w\s(),.%/-]+$")

TOP_KEYS = {"root", "nodes", "selected"}
NODE_KEYS = {
    "label",
    "id",
    "summary",
    "body",
    "body_file",
    "badges",
    "fields",
    "link",
    "children",
    "expanded",
    "icon",
}

#: Named badge colours; the stylesheet maps each to a light and a dark value.
NAMED_COLOURS = {"green", "orange", "amber", "red", "blue", "purple", "grey"}

#: Used outside Zensical, where there is no site configuration to copy.
FALLBACK_EXTENSIONS = [
    "admonition",
    "attr_list",
    "md_in_html",
    "tables",
    "pymdownx.highlight",
    "pymdownx.inlinehilite",
    "pymdownx.superfences",
]

_FILE = (
    '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>'
    '<path d="M14 3v5h5"/>'
)
ICONS = {
    "folder": (
        '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8'
        'a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
    ),
    "file": _FILE,
    "code": _FILE + '<path d="m10 12-2 2.5 2 2.5M14 12l2 2.5-2 2.5"/>',
    "config": _FILE
    + '<circle cx="12" cy="14.5" r="2"/><path d="M12 11v1.5M12 16.5V18"/>',
    "md": _FILE + '<path d="M8 17v-4l2 2 2-2v4M15 13v4m-1.5-1.5L15 17l1.5-1.5"/>',
}
SUFFIX_ICONS = {
    **dict.fromkeys(
        "py js mjs ts tsx jsx rs go c h cpp java rb php sh bash zsh fish lua r jl"
        " swift kt scala cs html css scss vue svelte".split(),
        "code",
    ),
    **dict.fromkeys(
        "toml yaml yml json jsonc ini cfg conf env lock xml properties".split(),
        "config",
    ),
    "md": "md",
    "markdown": "md",
}


class DirtreeError(SuperFencesException):
    """An invalid ``dirtree`` block. Fails the build with a located message."""


# -- data model ----------------------------------------------------------------


@dataclass
class Node:
    spec: dict[str, Any]
    label: str
    path: str  # label path, used in error messages: "src/main.py"
    parent: Node | None
    children: list[Node] = field(default_factory=list)
    id: str = ""

    @property
    def is_folder(self) -> bool:
        return self.label.endswith("/") or "children" in self.spec

    @property
    def ancestors(self) -> list[Node]:
        chain, node = [], self.parent
        while node:
            chain.insert(0, node)
            node = node.parent
        return chain

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "node"


def _icon(name: str) -> str:
    return (
        f'<svg class="dirtree__icon dirtree__icon--{name}" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="1.75" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f"{ICONS[name]}</svg>"
    )


# -- Zensical integration -------------------------------------------------------


def _zensical_context(md: Markdown) -> Any | None:
    """Return Zensical's rendering context (page and site config), if any."""
    try:
        from zensical.extensions.context import ContextPreprocessor  # noqa: PLC0415
    except ImportError:
        return None
    return ContextPreprocessor.from_markdown(md)


def _highlight(md: Markdown) -> Any | None:
    """Return the highlight extension SuperFences uses on ``md``."""
    if "fenced_code_block" not in md.preprocessors:
        return None
    fenced = md.preprocessors["fenced_code_block"]
    fenced.get_hl_settings()
    ext = getattr(fenced, "highlight_ext", None)
    return ext if hasattr(ext, "pygments_code_block") else None


_watch_warned = False


def _warn_if_unwatched(config: dict[str, Any], base: Path) -> None:
    """Zensical caches pages by their own source, so without ``watch`` an edited
    body file is ignored by ``serve`` and even by ``build``."""
    global _watch_warned  # noqa: PLW0603
    if _watch_warned:
        return
    root = Path(config["root_dir"]).resolve()
    for entry in config.get("watch") or []:
        watched = (root / entry).resolve()
        if base == watched or base.is_relative_to(watched):
            return
    _watch_warned = True
    log.warning(
        "zensical_dirtree: base_path %s is not listed under [project] watch, so "
        "edits to body files are not picked up until the embedding page changes. "
        'Add: watch = ["%s"]',
        base,
        base.relative_to(root) if base.is_relative_to(root) else base,
    )


# -- rendering -------------------------------------------------------------------


class _Renderer:
    """Render one fence. Holds the nested Markdown instance for node bodies."""

    def __init__(self, ext: DirtreeExtension, md: Markdown) -> None:
        self.ext = ext
        self.md = md
        self.context = _zensical_context(md)
        self.page = self.context.page.path if self.context else "<page>"
        self._inner: Markdown | None = None

    # -- errors

    def error(self, message: str, node: Node | None = None) -> DirtreeError:
        where = f"node '{node.path}': " if node else ""
        return DirtreeError(f"dirtree: {self.page}: {where}{message}")

    # -- Markdown

    @property
    def inner(self) -> Markdown:
        if self._inner is None:
            if self.context:
                config = self.context.config
                self._inner = Markdown(
                    extensions=config["markdown_extensions"],
                    extension_configs=config["mdx_configs"],
                )
            else:
                outer = _highlight(self.md)
                configs = {"pymdownx.highlight": outer.getConfigs()} if outer else {}
                self._inner = Markdown(
                    extensions=FALLBACK_EXTENSIONS, extension_configs=configs
                )
        return self._inner

    def markdown(self, text: str) -> str:
        # Carry the code block counter across, so line anchors
        # (__codelineno-N-M) stay unique on the page.
        inner, outer_hl = self.inner, _highlight(self.md)
        inner.reset()
        inner_hl = _highlight(inner)
        if outer_hl and inner_hl:
            inner_hl.pygments_code_block = outer_hl.pygments_code_block
        html = inner.convert(text)
        if outer_hl and inner_hl:
            outer_hl.pygments_code_block = inner_hl.pygments_code_block
        return html

    def inline(self, text: str) -> str:
        html = self.markdown(text).strip()
        match = re.fullmatch(r"<p>(.*)</p>", html, re.S)
        return match.group(1) if match else html

    # -- parsing

    def parse(self, source: str) -> tuple[str | None, list[Node], str]:
        try:
            data = yaml.safe_load(source)
        except yaml.YAMLError as error:
            raise self.error(f"invalid YAML: {error}") from None
        if not isinstance(data, dict):
            raise self.error("block must be a mapping with a 'nodes' list")
        for key in data:
            if key not in TOP_KEYS:
                raise self.error(f"unknown key '{key}'")
        specs = data.get("nodes")
        if not isinstance(specs, list) or not specs:
            raise self.error("'nodes' must be a non-empty list")

        nodes = [self.build(spec, None) for spec in specs]
        self.assign_ids(nodes)

        root = data.get("root")
        selected = data.get("selected", nodes[0].id)
        if selected not in {n.id for top in nodes for n in top.walk()}:
            raise self.error(f"selected: unknown node id '{selected}'")
        return (str(root) if root is not None else None), nodes, str(selected)

    def build(self, spec: Any, parent: Node | None) -> Node:
        prefix = f"{parent.path}/" if parent else ""
        if not isinstance(spec, dict):
            raise self.error(f"under '{prefix or 'nodes'}': node must be a mapping")
        label = spec.get("label")
        if label is None or isinstance(label, (dict, list)) or str(label) == "":
            raise self.error(f"under '{prefix or 'nodes'}': node needs a 'label'")
        label = str(label)
        node = Node(spec, label, prefix + label.rstrip("/"), parent)
        self.validate(node)
        node.children = [self.build(c, node) for c in spec.get("children") or []]
        return node

    def validate(self, node: Node) -> None:
        spec = node.spec
        for key in spec:
            if key not in NODE_KEYS:
                raise self.error(f"unknown key '{key}'", node)
        if "body" in spec and "body_file" in spec:
            raise self.error("has both 'body' and 'body_file'; use one", node)
        for key in ("summary", "body", "body_file", "link", "id"):
            if key in spec and not isinstance(spec[key], str):
                raise self.error(f"'{key}' must be a string", node)
        if "id" in spec and not ID_RE.match(spec["id"]):
            raise self.error(f"id '{spec['id']}' may only use [A-Za-z0-9_-]", node)
        if "children" in spec and not isinstance(spec["children"], (list, type(None))):
            raise self.error("'children' must be a list", node)
        if "expanded" in spec and not isinstance(spec["expanded"], bool):
            raise self.error("'expanded' must be true or false", node)
        if "icon" in spec and spec["icon"] not in ICONS:
            raise self.error(
                f"unknown icon '{spec['icon']}'; use one of {', '.join(ICONS)}", node
            )
        badges = spec.get("badges", [])
        if not isinstance(badges, list):
            raise self.error("'badges' must be a list", node)
        for badge in badges:
            if str(badge) not in self.ext.badges:
                raise self.error(f"unknown badge '{badge}'", node)
        fields = spec.get("fields", [])
        if not isinstance(fields, list) or not all(
            isinstance(f, dict) and "label" in f and "value" in f for f in fields
        ):
            raise self.error("'fields' must be a list of {label, value}", node)

    def assign_ids(self, nodes: list[Node]) -> None:
        taken = self.ext.used_ids
        every = [n for top in nodes for n in top.walk()]
        explicit = set()
        for node in every:
            if "id" in node.spec:
                node.id = node.spec["id"]
                if node.id in taken or node.id in explicit:
                    raise self.error(f"duplicate id '{node.id}'", node)
                explicit.add(node.id)
        for node in every:
            if not node.id:
                base = "-".join(_slug(n.label) for n in [*node.ancestors, node])
                node.id, n = base, 2
                while node.id in taken or node.id in explicit:
                    node.id, n = f"{base}-{n}", n + 1
            taken.add(node.id)

    # -- HTML

    def icon_for(self, node: Node) -> str:
        if "icon" in node.spec:
            return node.spec["icon"]
        if node.is_folder:
            return "folder"
        name = node.label.lower()
        if "." not in name.lstrip("."):
            return "config" if name.startswith(".") else "file"
        return SUFFIX_ICONS.get(name.rsplit(".", 1)[1], "file")

    def render(self, source: str) -> str:
        root, nodes, selected = self.parse(source)
        label = escape(root or "Directory tree", quote=True)
        root_html = (
            f'<span class="dirtree__root">{_icon("folder")}{escape(root)}</span>'
            if root
            else ""
        )
        every = [n for top in nodes for n in top.walk()]
        return (
            f'<div class="dirtree" data-dirtree data-selected="{escape(selected)}">'
            '<div class="dirtree__side"><div class="dirtree__bar">'
            f"{root_html}"
            '<button type="button" class="dirtree__toggle-all" '
            "data-dirtree-toggle-all hidden>Expand all</button></div>"
            f'<nav class="dirtree__tree" role="tree" aria-label="{label}">'
            f'<ul role="group">{"".join(self.item(n) for n in nodes)}</ul>'
            "</nav></div>"
            '<div class="dirtree__panels">'
            f"{''.join(self.panel(n, root) for n in every)}</div>"
            '<p class="dirtree__live" aria-live="polite" data-dirtree-live></p>'
            "</div>"
        )

    def item(self, node: Node) -> str:
        expanded = ""
        arrow = '<span class="dirtree__arrow" aria-hidden="true"></span>'
        if node.is_folder:
            state = "true" if node.spec.get("expanded") else "false"
            expanded = f' aria-expanded="{state}"'
            arrow = (
                '<span class="dirtree__arrow dirtree__arrow--folder" '
                'aria-hidden="true" data-dirtree-arrow></span>'
            )
        group = ""
        if node.children:
            group = (
                f'<ul role="group">{"".join(self.item(c) for c in node.children)}</ul>'
            )
        return (
            f'<li role="treeitem"{expanded} data-node="{node.id}">'
            f'<span class="dirtree__row">{arrow}'
            f'<a class="dirtree__link" href="#{PREFIX}{node.id}">'
            f"{_icon(self.icon_for(node))}"
            f'<span class="dirtree__label">{escape(node.label)}</span></a></span>'
            f"{group}</li>"
        )

    def panel(self, node: Node, root: str | None) -> str:
        spec, pid = node.spec, f"{PREFIX}{node.id}"
        parts = [self.crumbs(node, root)]
        parts.append(
            f'<p class="dirtree__title" id="{pid}-title">'
            f"{_icon(self.icon_for(node))}<span>{escape(node.label)}</span></p>"
        )
        if "summary" in spec:
            parts.append(f'<p class="dirtree__summary">{self.summary(node)}</p>')
        if spec.get("badges"):
            parts.append(
                '<p class="dirtree__badges">'
                + "".join(self.badge(str(b), node) for b in spec["badges"])
                + "</p>"
            )
        if spec.get("fields"):
            rows = "".join(
                f'<div class="dirtree__field"><dt>{escape(str(f["label"]))}</dt>'
                f"<dd>{self.inline(str(f['value']))}</dd></div>"
                for f in spec["fields"]
            )
            parts.append(f'<dl class="dirtree__fields">{rows}</dl>')
        body = self.body(node)
        if body:
            parts.append(f'<div class="dirtree__body">{body}</div>')
        if "link" in spec:
            href = escape(spec["link"], quote=True)
            parts.append(
                f'<p class="dirtree__more"><a href="{href}">Full docs →</a></p>'
            )
        if node.children:
            entries = "".join(
                f'<li><a href="#{PREFIX}{c.id}">{_icon(self.icon_for(c))}'
                f"{escape(c.label)}</a>"
                + (f" — {self.summary(c)}" if "summary" in c.spec else "")
                + "</li>"
                for c in node.children
            )
            parts.append(
                '<div class="dirtree__contents">'
                '<p class="dirtree__contents-title">Contents</p>'
                f"<ul>{entries}</ul></div>"
            )
        return (
            f'<section class="dirtree__panel" id="{pid}" data-panel="{node.id}" '
            f'aria-labelledby="{pid}-title">{"".join(parts)}</section>'
        )

    def crumbs(self, node: Node, root: str | None) -> str:
        """The node's path, ``root / src / main.py``; ancestors link to panels."""
        items = [escape(root.rstrip("/"))] if root else []
        items += [
            f'<a href="#{PREFIX}{a.id}">{escape(a.label.rstrip("/"))}</a>'
            for a in node.ancestors
        ]
        items.append(
            f'<span class="dirtree__crumb-current">{escape(node.label.rstrip("/"))}'
            "</span>"
        )
        sep = '<span class="dirtree__sep"> / </span>'
        return f'<p class="dirtree__crumbs">{sep.join(items)}</p>'

    def summary(self, node: Node) -> str:
        return self.inline(node.spec["summary"])

    def badge(self, key: str, node: Node) -> str:
        conf = self.ext.badges[key]
        if not isinstance(conf, dict):
            raise self.error(f"badge '{key}' must be configured as {{label, color}}")
        label = escape(str(conf.get("label", key)))
        colour = str(conf.get("color", "grey"))
        if colour in NAMED_COLOURS:
            return (
                f'<span class="dirtree__badge dirtree__badge--{colour}">{label}</span>'
            )
        if not COLOUR_RE.match(colour):
            raise self.error(f"badge '{key}' has an unsafe colour {colour!r}", node)
        return (
            f'<span class="dirtree__badge" style="--dirtree-badge: {colour}">'
            f"{label}</span>"
        )

    def body(self, node: Node) -> str:
        if "body" in node.spec:
            return self.markdown(node.spec["body"])
        if "body_file" in node.spec:
            return self.markdown(self.read_body_file(node))
        return ""

    def read_body_file(self, node: Node) -> str:
        if self.context:
            root = Path(self.context.config["root_dir"]).resolve()
        else:
            root = Path.cwd().resolve()
        base = (root / self.ext.getConfig("base_path")).resolve()
        if not base.is_relative_to(root):
            raise self.error(f"base_path {base} is outside the project root {root}")
        if self.context:
            _warn_if_unwatched(self.context.config, base)
        target = (base / node.spec["body_file"]).resolve()
        if not target.is_relative_to(root):
            raise self.error(
                f"body_file resolves to {target}, outside the project root {root}",
                node,
            )
        if not target.is_file():
            raise self.error(f"body_file not found: {target}", node)
        return target.read_text(encoding="utf-8")


# -- extension -------------------------------------------------------------------


class _RegisterFence(Preprocessor):
    """Add the ``dirtree`` fence to this Markdown instance's SuperFences."""

    def __init__(self, md: Markdown, ext: DirtreeExtension) -> None:
        super().__init__(md)
        self.ext = ext

    def run(self, lines: list[str]) -> list[str]:
        fenced = (
            self.md.preprocessors["fenced_code_block"]
            if "fenced_code_block" in self.md.preprocessors
            else None
        )
        superfences = getattr(fenced, "extension", None)
        if not hasattr(superfences, "extend_super_fences"):
            if any(FENCE_RE.match(line) for line in lines):
                page = _zensical_context(self.md)
                raise DirtreeError(
                    f"dirtree: {page.page.path if page else '<page>'}: the "
                    "'dirtree' fence needs pymdownx.superfences; add it to "
                    "markdown_extensions"
                )
            return lines
        if not any(entry["name"] == FENCE for entry in superfences.superfences):
            superfences.extend_super_fences(
                FENCE, self.ext.format, lambda *_args: True, None
            )
        return lines


class DirtreeExtension(Extension):
    def __init__(self, **kwargs: Any) -> None:
        self.config = {
            "base_path": [".", "Where body_file paths resolve, from the project root."],
            "badges": [{}, "Badge definitions: key -> {label, color}."],
        }
        super().__init__(**kwargs)
        self.used_ids: set[str] = set()

    @property
    def badges(self) -> dict[str, Any]:
        return self.getConfig("badges") or {}

    def extendMarkdown(self, md: Markdown) -> None:  # noqa: N802 - Markdown API
        md.registerExtension(self)
        md.preprocessors.register(
            _RegisterFence(md, self), "dirtree_register", REGISTER_PRIORITY
        )

    def reset(self) -> None:
        self.used_ids = set()

    def format(self, src: str, language: str, md: Markdown, **_kwargs: Any) -> str:
        return _Renderer(self, md).render(src)


def makeExtension(**kwargs: Any) -> DirtreeExtension:  # noqa: N802 - Markdown API
    return DirtreeExtension(**kwargs)
