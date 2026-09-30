The entry point. Loaded from `snippets/main-py.md` via `body_file`, so it can
be edited without touching the page.

```python
from app import create_app

if __name__ == "__main__":
    create_app().run(port=8080)
```
