The processing entry point. Its description lives in `snippets/process-py.md`
and is referenced from the tree file with `body_file`, exactly as from a fence.

```python
import xarray as xr


def process(raw: str, out: str) -> None:
    ds = xr.open_dataset(raw)
    ds.where(ds.qc_flag == 0).to_netcdf(out)
```
