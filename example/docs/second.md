# Second page

Navigate back and forth between pages to check that the explorer re-binds
after instant navigation without doubling its listeners.

````dirtree
root: tiny/
nodes:
  - label: pyproject.toml
    summary: Package metadata
    body: |
      ```toml
      [project]
      name = "tiny"
      ```
  - label: tiny/
    children:
      - label: __init__.py
        summary: Makes `tiny` a package
````

[Jump to `src/main.py` on the first page](index.md#dirtree-src-main-py)
