# Design notes

Why the code looks the way it does: the goals it serves, the Zensical
behaviour it depends on, and the decisions taken along the way. Findings were
verified against Zensical 0.0.67 and pymdown-extensions 12.1 (2026-09/10);
re-check the "Zensical behaviour" section when upgrading Zensical, which is
pre-1.0.

## Goals and constraints

- The tree and every node's description are **static HTML rendered at build
  time**, so search indexes them and the page reads as a nested list followed
  by all descriptions **without JavaScript**.
- The script only adds interactivity: vanilla JS, no framework, no build step,
  re-initialised through Zensical's `document$` after instant navigation.
- Node bodies are ordinary Markdown rendered with **the site's own Markdown
  settings**, so code blocks, admonitions and links look exactly like the rest
  of the page.
- Panel titles and body headings must **not enter the page's table of
  contents**.
- Theme colours come from Zensical's CSS variables; only the badge and icon
  palettes are defined by the extension.
- Nothing to set up beyond the Markdown extension: the stylesheet and script
  ship inside it (see "Assets are inlined" below).

## Zensical behaviour the extension relies on

**Fresh Markdown instance per page.** Zensical builds
`Markdown(extensions=config["markdown_extensions"], …)` for every page
(`zensical/markdown/render.py`). SuperFences reads its fence list
(`ext.superfences`) when its preprocessor runs and exposes
`extend_super_fences()`.
→ A preprocessor at priority 27, just before SuperFences' own (25), registers
the `dirtree` fence on each instance. Verified with the extension listed both
before and after `pymdownx.superfences`.

**Naming any Markdown extension replaces the defaults.** Zensical uses
`config.get("markdown_extensions", DEFAULTS)`, so one
`[project.markdown_extensions.*]` table drops its whole default set, including
SuperFences.
→ Documented in the README; a `dirtree` fence without SuperFences is a clear
build error instead of raw text.

**SuperFences swallows formatter exceptions.** Any exception from a custom
fence formatter except `SuperFencesException` is caught and the block is
emitted as plain code, so the build passes.
→ `DirtreeError` subclasses `SuperFencesException`; a broken tree fails
`zensical build` with exit code 1.

**The page cache is keyed on the page's own source.** An edited file outside
the page (body file, tree file) changes nothing for the cache: `serve` does not
rebuild and even `build` reuses the stale page. Files listed under
`[project] watch` are hashed into the configuration, which invalidates the
cache. `watched_files` is computed while the configuration is parsed, before
any extension loads, so the extension cannot add paths itself.
→ The extension logs a one-time warning when `base_path` is not covered by
`watch`; users run `zensical build --clean` after upgrading the package.

**Nested rendering restarts highlight counters.** A nested Markdown instance
starts pymdownx.highlight's block counter at zero, producing duplicate line
anchors such as `__codelineno-0-1`.
→ The counter is copied into the nested instance and back out after each body.

**The rendering context carries page and config.** Zensical registers a
`ContextPreprocessor` holding the current page (`page.path`) and the full
configuration (`root_dir`, `watch`, `markdown_extensions`, `mdx_configs`).
→ Used for error messages, for resolving `base_path`, and to build the nested
Markdown instance with the site's own settings. Outside Zensical (tests, plain
Python-Markdown) a fixed fallback extension set is used.

**Links are rewritten twice.** Zensical's `LinksExtension` postprocessor also
rewrites links inside the stashed widget HTML (`link: reference.md` →
`reference/`), and instant navigation rewrites in-content hrefs to absolute
URLs in the browser.
→ The script compares `a.pathname`/`a.hash` instead of matching `href^="#"`.

**Everything under `docs/` becomes a page.** That includes folders starting
with `_`. MkDocs' `exclude_docs` is ignored; the `exclude` plugin
(`[project.plugins.exclude] glob = [...]`) works.

**Extensions cannot register assets.** Zensical has no third-party plugin API
and fixes `extra_css` / `extra_javascript` before extensions load, so an
extension can only emit its stylesheet and script inside its own HTML.

**Instant navigation re-runs inline scripts.** It re-creates every `<script>`
in the swapped-in content, so inline scripts run on navigated pages too.
Verified with Playwright and `site_url` set (instant navigation is off without
it): starting on a page with no tree and navigating to tree pages and back,
every widget initialises without errors.
→ `window.__dirtreeLoaded` makes the repeated run harmless.

**Cascade order of an inline `<style>`.** A `<style>` in the body comes after
`extra_css`, so it beats a user override of equal specificity. Moving the CSS
into a cascade layer (`@layer dirtree`) fixed that but broke the layout:
layered rules lose to *all* unlayered CSS, including the theme's
`.md-typeset ul/li` margins and bullets.
→ The CSS stays unlayered; the `--dirtree-*` defaults sit in
`:where(.dirtree)` and `:where([data-md-color-scheme="slate"]) .dirtree`, so
the documented override selectors still win. Other overrides need a more
specific selector. The inlined text stays out of `search.json`.

## Decisions

**Assets are inlined by default** (2026-10-01). The extension emits the
stylesheet and script before the first tree on each page, so users configure
nothing but the extension. The cost is about 6 KB gzipped per page with a tree,
not shared between pages, and a Content Security Policy must allow inline
scripts. `inline_assets = false` restores the earlier setup: the
`zensical-dirtree install` command copies both files into `docs/` for
`extra_css` / `extra_javascript`.

**The fence registers itself** rather than requiring a `custom_fences` entry.
A manual entry (with a dotted `format` path, which Zensical resolves) would
work too, but costs users a second configuration block for nothing.

**Trees always open on their first node.** A per-tree `selected` key existed
at first and was removed (2026-10-01) so the initial view is predictable. Deep
links still select any node; on a page with several trees, the trees a link
does not point into still open on their first node.

**Long Contents lists are capped.** A folder's Contents list shows
`contents_limit` entries (default 10, settable per tree), then a "Show N more"
button. The extra entries are marked at build time and hidden only once the
script runs, so without JavaScript the full list shows. Large folders otherwise
produced very tall panels.

**Summaries double as tree-row tooltips.** A node's summary is also the native
`title` of its tree row, with Markdown stripped because attributes hold plain
text.

**Strict validation.** Unknown keys at any level are build errors (they are
almost always typos), and explicit ids are limited to `[A-Za-z0-9_-]`, which
is safe in URLs and CSS selectors.

**ARIA roles are in the static HTML.** The tree markup carries `role="tree"`,
`treeitem` and `aria-expanded` from the start; without JavaScript, collapsed
folders still show their children so that all content stays visible.

**Body files stay outside `docs/`.** Placing them next to their pages
(tested 2026-10-01) needs the `exclude` plugin, whose absence fails silently
with stray pages in the site and search; it still needs `watch`, and relative
links in bodies still resolve against the embedding page. It adds a required
setting and saves nothing.

**Large or reused trees go into YAML files** (`src:`) in the same format as a
fence, resolved like `body_file`. JSON was rejected (no comments, no multi-line
strings for prose), as was a custom Markdown format for whole trees (a second
format to design and parse while `body_file` already covers long prose).

**The JSON Schema is for editors only.** It gives completion and live checks in
tree files; the build keeps its own validator, whose errors name the page, tree
file and node. Tests keep the two in agreement.

**The CLI uses argparse**, as zensical-vars does; two subcommands do not justify
a Typer dependency.
