# Implementation notes

Investigated against zensical 0.0.67 and pymdown-extensions 12.1 on 2026-09-30.

## Findings

### Superfences fence registration under Zensical → self-registration

- Zensical creates a fresh `Markdown(extensions=config["markdown_extensions"], …)`
  per page (`zensical/markdown/render.py`). SuperFences reads its fence list
  (`ext.superfences`) at preprocessor run time and exposes `extend_super_fences()`.
- A preprocessor at priority 27 registers the fence before SuperFences runs
  (25). Verified in real builds with `zensical_dirtree` listed both before and
  after `pymdownx.superfences`.
- The manual alternative (a `custom_fences` entry whose `format` is a dotted
  string, which Zensical resolves) would also work, but it needs a second
  config block for no gain. Rejected.
- Setting any `[project.markdown_extensions.*]` table replaces Zensical's entire
  default extension set (`config.get("markdown_extensions", DEFAULTS)`), which
  removes SuperFences. Documented. A page with a `dirtree` fence but no
  SuperFences raises a clear error.
- SuperFences catches every exception from a formatter except
  `SuperFencesException` and emits a plain code block, so the build passes
  silently. Errors therefore subclass `SuperFencesException`. Verified:
  `zensical build` exits 1.

### Live reload of files outside docs/ → requires `[project] watch`

- Without `watch`: editing a `base_path` file triggers no rebuild in `serve`.
  Worse, `zensical build` also reuses the cached page (cache keyed on page
  source) until the embedding page's text changes. `touch` alone isn't enough.
- With `watch = ["snippets"]`: `serve` rebuilds and reloads on each edit, and
  `build` picks up changes.
- `watched_files` is computed in `_apply_defaults` while parsing config, before
  any extension loads, so an extension cannot add paths. The extension logs a
  one-time warning when `base_path` is not under a `watch` entry.

### Other verified behaviour

- A nested renderer reset the highlight block counter, producing duplicate
  `__codelineno-0-1` ids. Fixed by carrying `pygments_code_block` across.
- Zensical's instant navigation rewrites in-content hrefs to absolute URLs, so
  JS compares `a.pathname`/`a.hash` instead of matching `href^="#"`.
- Zensical's `LinksExtension` postprocessor also rewrites links inside the
  stashed widget HTML (e.g. `link: reference.md` → `reference/`).

## Deviations

- Added a build-time warning when `base_path` isn't watched (not in the spec;
  follows from the live-reload finding).
- Unknown node or top-level keys are build errors (catches typos). The spec lists
  only the specific error cases.
- Explicit ids are restricted to `[A-Za-z0-9_-]` so they are safe in URLs and
  selectors.
- ARIA roles are emitted in the static HTML as the spec's markup shows. Without
  JS, `aria-expanded="false"` folders still show their children (all content
  visible, per the no-JS requirement).
- The CLI uses argparse (mirrors zensical-vars; one subcommand does not justify
  a Typer dependency).
- The README install section leads with `uv add git+…` and gives the pip form
  as the alternative.
