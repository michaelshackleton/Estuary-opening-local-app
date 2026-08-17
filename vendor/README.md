# vendor/

Verbatim copies of the files this app needs from the parent `rs-utils-main`
repository's `src/` folder, copied in so that `Claude_script` is fully
self-contained and can be moved or copied to any location (a different
drive, a network share, another machine) without needing the rest of
`rs-utils-main` alongside it.

Copied from `src/` (unmodified):

- `rs_data.py` - `STACDataManager`, `STACRSRegionManager`
- `rs_processing.py` - `RSDataProductManager`
- `utils.py` - used by `rs_data.py` for rasterising vector layers
- `rsderiv/__init__.py`, `rsderiv/sharpen.py`, `rsderiv/sen1.py` - used by
  `rs_processing.py` for pan-sharpening and (unused by this app, but
  imported regardless) Sentinel-1 speckle filtering

`rsderiv/__init__.py` is empty, so no other files from the original
`rsderiv` package (`indices.py`, `kernel_idx.py`, `transform.py`) are
pulled in - this is the complete set actually needed.

If the original scripts in `src/` are updated with bug fixes or new
features you want here, these vendored copies won't pick that up
automatically - they'd need to be re-copied by hand.
