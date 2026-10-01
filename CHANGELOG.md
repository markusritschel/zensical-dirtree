# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

After upgrading, rebuild once with `zensical build --clean` (cached pages hold
the previous version's inlined stylesheet and script). Re-run
`zensical-dirtree schema --output …` if you use tree files, and
`zensical-dirtree install --docs-dir docs` if you set `inline_assets = false`.

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
- A folder's Contents list shows `contents_limit` entries (default 10, set per
  tree), then a "Show N more" button; without JavaScript the full list shows.
- A node's summary also appears as a tooltip on its tree row.
- Every tree opens on its first node; deep links select any other node.
- Whole trees in their own YAML files, loaded with `src:`, and a bundled JSON
  Schema for editor completion and validation (`zensical-dirtree schema`).
- Keyboard navigation (WAI-ARIA tree pattern), deep links (`#dirtree-<id>`),
  expand/collapse all, instant-navigation support, light and dark mode, and a
  stacked layout on narrow screens.
- Build errors that name the page, the tree file and the node.
- The stylesheet and script are inlined before the first tree on each page, so
  there is nothing to set up besides the Markdown extension. For a strict
  Content Security Policy, `inline_assets = false` and
  `zensical-dirtree install` copy them into `docs/` instead.

[Unreleased]: https://github.com/markusritschel/zensical-dirtree/commits/develop
