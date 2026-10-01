# zensical-dirtree

An interactive directory-tree explorer for [Zensical](https://zensical.org)
documentation sites: a clickable tree on the left, a detail panel on the right.
Each node's description is ordinary Markdown, so code blocks, admonitions and
links look exactly like the rest of your page.

The explorer is rendered to static HTML at build time. A small script (no
dependencies) adds the interactivity, so the content is indexed by search, works
with instant navigation and light/dark mode, and stays readable with JavaScript
disabled.

## Install

```bash
uv add git+https://github.com/markusritschel/zensical-dirtree
# or: pip install git+https://github.com/markusritschel/zensical-dirtree
zensical-dirtree install --docs-dir docs
```

The last command copies `dirtree.css` and `dirtree.js` into
`docs/stylesheets/` and `docs/javascripts/`. Re-run it after upgrading.

## Configure

In `zensical.toml`:

```toml
[project]
extra_css = ["stylesheets/dirtree.css"]
extra_javascript = ["javascripts/dirtree.js"]
watch = ["snippets"]            # same as base_path; see below

[project.markdown_extensions.pymdownx.superfences]
# ... plus Zensical's other default extensions, see below

[project.markdown_extensions.zensical_dirtree]
base_path = "snippets"          # where body_file paths resolve; outside docs/
badges.committed = { label = "committed", color = "green", indicator = true }
badges.gitignored = { label = "gitignored", color = "orange", indicator = true }
badges.generated = { label = "generated", color = "amber" }
```

Things to know:

- **No `custom_fences` entry needed.** The extension registers the `dirtree`
  fence with `pymdownx.superfences` itself, in whatever order the extensions
  are listed. SuperFences must be enabled, and the build fails with a clear
  message if a page uses a `dirtree` fence without it.
- **Naming any Markdown extension replaces Zensical's defaults.** As soon as
  `zensical.toml` contains one `[project.markdown_extensions.*]` table, Zensical
  drops its whole built-in set (SuperFences, highlighting, admonitions, …).
  List them again next to `zensical_dirtree`. Sites created with `zensical new`
  already list them all; otherwise copy the complete default list from
  [`example/zensical.toml`](example/zensical.toml).
- **Add `base_path` to `watch`.** Zensical caches each page by its own source.
  Without `watch`, an edited body file is ignored by `zensical serve` **and by
  `zensical build`** until the page that embeds it changes. With it, every edit
  rebuilds. The extension logs a warning when `base_path` isn't covered by
  `watch`.

### Badge colours

Named colours adapt to light and dark mode: `green`, `orange`, `amber`, `red`,
`blue`, `purple`, `grey` (the default). Any other value is used as a raw CSS
colour, e.g. `color = "#0e7490"` or `color = "rgb(14 116 144)"`.

### Status dots

Badges with `indicator = true` also appear as a coloured dot at the right edge
of the node's row in the tree, like a git status marker. If a node has several
indicator badges, the first one listed on the node is shown. The dot's tooltip
is the badge label, which screen readers also announce with the item.

### Icon colours

Icons are coloured by type, with light and dark values. Override the custom
properties in a stylesheet of your own to match your palette:

```css
.dirtree {
  --dirtree-icon-folder: #c98a1a;
  --dirtree-icon-code: #2f76c4;
  --dirtree-icon-config: #6b7689;
  --dirtree-icon-md: #8a5fd1;
  --dirtree-icon-file: #7d8590;
}
```

For dark mode, set them under `[data-md-color-scheme="slate"] .dirtree`.
The tree pane's shading works the same way: `--dirtree-tree-bg` (and
`--dirtree-tree-hover` for hovered rows); set it to `transparent` for no shading.

## Syntax

Use four backticks for the outer fence so bodies can contain ordinary
triple-backtick code blocks. The content is YAML.

`````markdown
````dirtree
root: your-project/
selected: config-toml
nodes:
  - label: zensical.toml
    id: config-toml
    badges: [committed]
    summary: Main configuration
    fields:
      - label: Read when
        value: At startup
    body: |
      Controls how the site is built. Example:

      ```toml
      [project]
      site_name = "My docs"
      ```
    link: reference/config.md
  - label: src/
    expanded: true
    children:
      - label: main.py
        body_file: main-py.md
````
`````

### Top level

| Key | Required | Notes |
| --- | --- | --- |
| `nodes` | yes | Non-empty list of nodes. |
| `root` | no | Label shown above the tree and at the start of each breadcrumb. |
| `selected` | no | Id of the node selected on load. Default: the first node. |
| `contents_limit` | no | Entries a folder's "Contents" list shows before a "Show N more" button. Default: 10. Without JavaScript the full list is shown. |

### Nodes

| Key | Type | Notes |
| --- | --- | --- |
| `label` | str | **Required.** Display name. A trailing `/` or a `children` key makes it a folder. |
| `id` | str | Slug for deep links (`[A-Za-z0-9_-]`). Default: the slugified label path, e.g. `src/main.py` → `src-main-py`. Must be unique on the page. |
| `summary` | str | One line under the title, also shown in the parent's "Contents" list. Inline Markdown. |
| `body` | str | Markdown. Mutually exclusive with `body_file`. |
| `body_file` | str | Markdown file, relative to `base_path`. |
| `badges` | list[str] | Keys from the badge configuration. |
| `fields` | list[{label, value}] | Label/value callouts. `value` is inline Markdown. |
| `link` | str | Adds a "Full docs →" link. Relative `.md` links are resolved like any page link. |
| `children` | list[node] | Makes the node a folder. |
| `expanded` | bool | Folder starts open. Default `false`. |
| `icon` | str | `folder`, `file`, `code`, `config` or `md`. Default: derived from type and extension. |

### Ids and deep links

Every node's panel has the id `dirtree-<id>`, so `[see main.py](#dirtree-src-main-py)`
selects that node from anywhere on the page, expands its folders, and scrolls
the explorer into view; links from other pages work too
(`page.md#dirtree-src-main-py`). Selecting a node updates the address bar.

Ids are unique across the whole page. When two nodes would get the same default
id, including across two trees on one page, the later one gets a `-2`, `-3`, …
suffix. Two explicit ids that clash are a build error.

Those suffixes follow the order of trees on the page, so they shift when a tree
is added above another or the same tree file is shown twice. On pages with
several trees, give an explicit `id` to every node you link to; explicit ids
never change.

### Errors

Mistakes fail the build with the page, node and cause, for example
`dirtree: index.md: node 'src/main.py': body_file not found: /…/snippets/main-py.md`.
This covers invalid YAML, unknown keys, `body` together with `body_file`, a
missing body file, a `body_file` or `base_path` outside the project root, unknown
badges or icons, unsafe badge colours, duplicate ids and an unknown `selected`.
For a tree loaded from a file, the message names the file too:
`dirtree: index.md: trees/project.yaml: node 'src': unknown icon 'rocket'`.

## Trees in their own files

A large tree, or one shown on several pages, can live in its own YAML file.
The fence then holds a single line:

````markdown
```dirtree
src: trees/project.yaml
```
````

The file has exactly the format of a fence's content (`root`, `selected`,
`nodes`). Its path resolves against `base_path`, like `body_file`, so with
`base_path = "snippets"` the file above is `snippets/trees/project.yaml`.
`body_file` paths inside it resolve against `base_path` as well. Keep
`watch = ["snippets"]` so edits to tree files rebuild the pages using them.

`src` stands alone: `root`, `selected` and `nodes` belong in the file, and a
tree file cannot load another one.

### Editor validation

The package ships a JSON Schema for tree files. Copy it next to them:

```bash
zensical-dirtree schema --output snippets/trees/dirtree.schema.json
```

and reference it from the first line of each tree file:

```yaml
# yaml-language-server: $schema=dirtree.schema.json
root: your-project/
nodes:
  - label: …
```

Editors with YAML language support (VS Code with the Red Hat YAML extension,
JetBrains IDEs, Neovim with yaml-language-server) then offer completion,
show each key's description on hover and flag mistakes as you type. The schema
is for editing only; the build still runs its own checks. Re-run the command
after upgrading.

## Behaviour

- Click a node to select it and show its panel. Clicking a folder also expands
  it. The arrow beside a folder only toggles it.
- Keyboard (WAI-ARIA tree pattern): <kbd>↑</kbd>/<kbd>↓</kbd> move through
  visible nodes, <kbd>→</kbd> expands or enters a folder, <kbd>←</kbd>
  collapses or moves to the parent, <kbd>Home</kbd>/<kbd>End</kbd> jump,
  <kbd>Enter</kbd>/<kbd>Space</kbd> select and toggle. The tree is a single tab stop.
- An icon button above the tree expands or collapses all folders; its label
  ("Expand all" / "Collapse all") shows as a tooltip and is read by screen
  readers. Enable Zensical's `content.tooltips` feature for styled tooltips.
- Selections are announced through a polite live region.
- Below 700px wide, the tree stacks above the panel.
- Without JavaScript: a nested list of links, followed by every node's
  description.

## Known limitations

- **Relative links inside a `body_file`** resolve relative to the page that
  embeds the tree, not to the body file.
- **Live reload of body files needs `watch`** (see [Configure](#configure)).
  Zensical fixes its watch list while reading the configuration, before
  extensions load, so the extension cannot add `base_path` itself.
- **Outside Zensical** (plain Python-Markdown, e.g. in tests), bodies render
  with a fixed standard extension set rather than the site's own.
- Headings inside a body get ids but never appear in the page's table of
  contents.
- One root per tree; put two trees on the page for two roots.

## Example site

`example/` exercises every feature: nesting, badges (named and raw colour),
fields, `body` and `body_file`, icon overrides, status dots, two trees on one
page, a table of deep links, a second page for instant navigation, and a tree
loaded from a schema-checked YAML file.

```bash
cd example && uv run zensical serve
```

## Development

```bash
uv sync
uv run pytest                   # unit tests + real Zensical builds of example/
uv run ruff check . && uv run ruff format --check .
uv run zensical-dirtree install --docs-dir example/docs   # after editing assets
uv run zensical-dirtree schema --output example/snippets/trees/dirtree.schema.json  # after editing the schema
```
