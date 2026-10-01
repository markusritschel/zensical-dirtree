# Explorer

A project layout, explained. Click an entry on the left, use the arrow keys,
or follow a deep link. Everything here is also plain HTML: with JavaScript
disabled it reads as a list followed by every description.

````dirtree
root: your-project/
selected: config-toml
nodes:
  - label: zensical.toml
    id: config-toml
    badges: [committed]
    summary: Main *configuration* for the site
    fields:
      - label: Read when
        value: At startup, and on every change during `zensical serve`
      - label: Format
        value: "[TOML](https://toml.io)"
    body: |
      Controls how the site is built. Settings live under `[project]`:

      ```toml
      [project]
      site_name = "My docs"
      watch = ["snippets"]
      ```

      !!! tip "Watch your snippets"
          Files under `base_path` live outside `docs/`, so list them under
          `watch` to rebuild when they change.
    link: reference.md
  - label: src/
    expanded: true
    summary: Application source code
    badges: [committed]
    children:
      - label: main.py
        summary: Entry point
        badges: [committed]
        body_file: main-py.md
      - label: settings.json
        summary: Runtime settings
        badges: [local]
        body_file: settings-json.md
      - label: vendor/
        summary: Third-party code, never edited by hand
        badges: [generated, gitignored]
        children:
          - label: lib.min.js
            badges: [generated]
            body: Minified bundle. Rebuilt by `make vendor`.
  - label: docs/
    summary: The documentation sources
    children:
      - label: index.md
        summary: Landing page
      - label: README.md
        icon: file
        summary: Uses an icon override (`file` instead of `md`)
  - label: .env
    badges: [gitignored, local]
    summary: Secrets for local development
    body: |
      Never commit this file.

      ```bash
      API_TOKEN=change-me
      ```
  - label: Makefile
    icon: code
    summary: Task runner
````

## Deep links

Every node has an address. These links select a node, expand its folder, and
scroll the explorer into view:

| Node | Link |
| --- | --- |
| `src/main.py` | [#dirtree-src-main-py](#dirtree-src-main-py) |
| `src/vendor/lib.min.js` | [#dirtree-src-vendor-lib-min-js](#dirtree-src-vendor-lib-min-js) |
| Second tree: `data/raw/` | [#dirtree-data-raw](#dirtree-data-raw) |

## A second tree on the same page

Ids are unique across the page, so two trees can sit side by side in the
document. The second one has no `root` label.

````dirtree
nodes:
  - label: data/
    expanded: true
    summary: Measurement data, raw and processed
    body: |
      Raw files are never edited: every correction happens in the processing
      step, so `processed.nc` can always be rebuilt from `raw/`.
    children:
      - label: raw/
        summary: Untouched instrument output
        badges: [gitignored]
        children:
          - label: 2026-09-30.csv
            summary: One day of underway measurements
      - label: processed.nc
        summary: Gridded, quality-controlled output
        badges: [generated]
        fields:
          - label: Written by
            value: "`make process`"
````
