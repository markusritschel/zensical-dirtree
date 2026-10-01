# zensical-dirtree

Python-Markdown extension that renders a `dirtree` fenced block (YAML) into a
static tree + detail-panel widget for Zensical sites, plus a vanilla-JS/CSS
asset pair that makes it interactive. The spec is in `SPEC.md`; findings and
deviations from building it are in `implementation-notes.md`.

```bash
uv sync
uv run pytest                              # unit + Zensical integration tests
uv run ruff check . && uv run ruff format --check .
cd example && uv run zensical serve        # manual check in a browser
```

## Architecture

A page's Markdown reaches Zensical's `render()`, which builds a fresh
`Markdown` instance per page. `DirtreeExtension.extendMarkdown` registers only a
preprocessor, `_RegisterFence`, at priority 27. When it runs, just before
SuperFences' own preprocessor (25), it looks up the SuperFences instance through
`md.preprocessors["fenced_code_block"].extension` and calls
`extend_super_fences("dirtree", …)`. This is why users need no `custom_fences`
entry and why the extension order doesn't matter.

SuperFences then calls `DirtreeExtension.format` for each fence, which builds a
`_Renderer`. The renderer parses and validates the YAML into `Node` objects,
assigns ids (explicit first, then slugged defaults with `-N` suffixes; the
extension's `used_ids` is shared by every tree on the page and reset per page),
and emits the HTML. Node bodies and inline fields go through a nested `Markdown`
instance built from Zensical's own config (`ContextPreprocessor` carries the page
and config), so code renders exactly like page code. The pymdownx.highlight
block counter is copied in and out around each nested render so line anchors
stay unique. The returned HTML is stashed by SuperFences, so panel titles and
body headings never reach the page TOC.

A fence holding only `src: <path>` is swapped for the YAML in that file before
validation (`_Renderer.load_tree_file`); from there it is rendered like an
inline tree. `src` and `body_file` share `_Renderer.resolve_file`, so both
resolve against `base_path` with the same project-root check, not-found error
and `watch` warning. While a tree file is rendered, `self.src` adds its path to
every error message.

`src/zensical_dirtree/dirtree.schema.json` documents the tree format for
editors (`zensical-dirtree schema` copies it out). It is never used at build
time. `tests/test_schema.py` keeps it in step with `TOP_KEYS`, `NODE_KEYS` and
`ICONS` and checks both give the same verdict on sample trees, so **edit the
schema whenever you change the node format**.

Errors are `DirtreeError(SuperFencesException)`. SuperFences deliberately
re-raises that class and swallows every other formatter exception, which would
otherwise leave a raw code block and a green build.

The assets live in `src/zensical_dirtree/assets/`. By default
`DirtreeExtension.format` prepends them inline to a page's first tree
(`assets_inlined` is reset per page like `used_ids`). Zensical re-runs inline
scripts on instant navigation. The CSS must not go into a cascade layer: that
would lose to the theme's `.md-typeset ul/li` rules too. Since it lands after
`extra_css`, the `--dirtree-*` defaults sit in `:where()` so the documented
overrides still win. With `inline_assets = false`, `cli.py` copies the assets
into a docs dir instead. `dirtree.js` initialises each `[data-dirtree]` via
`document$`, keeps per-widget state in a `WeakMap` (idempotent init), and registers one global
`hashchange` listener, guarded by `window.__dirtreeLoaded`.

`example/snippets/trees/dirtree.schema.json` is a **copy** made by the CLI.
Re-run `schema --output` after editing the original (a test fails when the
copy is stale).

## Known limitations & improvements

- [P2] Relative links inside a `body_file` resolve against the embedding page.
- [P2] `watch` must be set by the user (Zensical computes it before extensions load).
- [P3] Inlined assets (~6 KB gzipped) repeat on every page with a tree and
  need a CSP that allows inline scripts (`inline_assets = false` otherwise).
- [P3] Outside Zensical, bodies use the fixed `FALLBACK_EXTENSIONS` set.
- [P3] The browser checks (keyboard, deep links, instant navigation, no-JS) ran
  as a scratch Playwright script outside the suite; consider adding one.
- [P3] Placeholder: the GitHub URL in README.md assumes
  `github.com/markusritschel/zensical-dirtree`.
