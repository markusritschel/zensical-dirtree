# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

After upgrading, re-run `zensical-dirtree install --docs-dir docs` (the
stylesheet and script are copies) and `zensical-dirtree schema --output …` if
you use tree files, then rebuild once with `zensical build --clean`.

## [Unreleased]

First release.

### Added

- `dirtree` fence for Zensical pages: a clickable tree and a detail panel,
  rendered to static HTML at build time, so content is searchable and readable
  without JavaScript. The fence registers itself with `pymdownx.superfences`.
- Node bodies in Markdown, inline (`body`) or from a file (`body_file`),
  rendered with the site's own Markdown settings; summaries, fields, links and
  badges with named or raw colours.
- Badges marked `indicator = true` show as a status dot in the tree.
- Whole trees in their own YAML files, loaded with `src:`, and a bundled JSON
  Schema for editor completion and validation (`zensical-dirtree schema`).
- Keyboard navigation (WAI-ARIA tree pattern), deep links (`#dirtree-<id>`),
  expand/collapse all, instant-navigation support, light and dark mode, and a
  stacked layout on narrow screens.
- Build errors that name the page, the tree file and the node.
- `zensical-dirtree install` to copy the stylesheet and script into `docs/`.

[Unreleased]: https://github.com/markusritschel/zensical-dirtree/commits/develop
