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
uv run zensical-dirtree install --docs-dir example/docs   # after editing assets
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

Errors are `DirtreeError(SuperFencesException)`. SuperFences deliberately
re-raises that class and swallows every other formatter exception, which would
otherwise leave a raw code block and a green build.

The assets live in `src/zensical_dirtree/assets/`. `cli.py` copies them into a
docs dir. `dirtree.js` initialises each `[data-dirtree]` via `document$`, keeps
per-widget state in a `WeakMap` (idempotent init), and registers one global
`hashchange` listener, guarded by `window.__dirtreeLoaded`.

`example/docs/{stylesheets,javascripts}/dirtree.*` are **copies** made by the
CLI. Re-run the install command after editing the assets.

## Known limitations & improvements

- [P2] Relative links inside a `body_file` resolve against the embedding page.
- [P2] `watch` must be set by the user (Zensical computes it before extensions load).
- [P3] Outside Zensical, bodies use the fixed `FALLBACK_EXTENSIONS` set.
- [P3] The browser checks (keyboard, deep links, instant navigation, no-JS) ran
  as a scratch Playwright script outside the suite; consider adding one.
- [P3] Placeholder: the GitHub URL in README.md assumes
  `github.com/markusritschel/zensical-dirtree`.
