# Estuary Mouth Monitor (local desktop app)

Detects whether an estuary mouth is open or closed using satellite
imagery, and lets you view and analyse how often it closes over time.
Draw a region around the mouth, define the inside/outside lines (and
optional structures), pick a date range and cloud-cover threshold, and get
an open/closed/indeterminate time series sourced live from Digital Earth
Australia.

This is the local, run-on-your-own-machine counterpart to the hosted
version at [estuary-openings.streamlit.app](https://estuary-openings.streamlit.app) -
same map, same classification logic, same data source. The difference is
just where things are stored: this version saves site layers and cached
rasters to folders on your own computer via native Windows dialogs,
instead of through browser upload/download, and isn't limited by a shared
server's memory.

This app is fully self-contained - all the code it depends on is vendored
into `vendor/` (see `vendor/README.md`), so it can be copied or moved to
any drive or machine and will still run, with one catch (below).

## Setup (one-off)

```
cd "Estuary openings local app"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**If you move or copy this folder somewhere else, you must redo this step
at the new location.** A Python virtual environment (`.venv`) is not
portable - the activation scripts inside it have the exact original folder
path baked in, so a `.venv` created at `C:\...\Documents\...` will not work
once the folder is moved to a network drive or anywhere else. Delete the
old `.venv` folder and run the three commands above again from the new
location - everything else (the app, its config, saved sites) moves with
the folder just fine.

If the new location is a network drive, it's worth creating the `.venv`
directly on that drive too (not on a local drive with a shortcut/symlink
to the network location) - some Windows setups are slower or flakier
running Python packages, particularly compiled ones like `rasterio`/GDAL,
over a network share. If installs or startup are unreasonably slow, or you
see file-locking errors, that's the first thing to suspect.

## Running

Double-click `run_app.bat`, or from an activated environment:

```
cd "Estuary openings local app"
streamlit run app.py
```

This opens the app in your browser. It runs entirely locally - no data
leaves your machine except the STAC/raster requests to Digital Earth
Australia's own servers.

## Folder layout

- `app.py` - the Streamlit UI (map + draw tools + run controls + results).
- `modules/connectivity.py` - the NDWI/oa_fmask water-masking and
  path-connectivity logic. Framework-independent - no Streamlit or STAC
  code in here, so it can be unit tested on its own.
- `modules/region.py` - manages the drawn ROI/lines/structures layers,
  including saving/loading them as Esri Shapefiles (`roi.shp`, `lines.shp`,
  `structures.shp`) so an analysis can be reproduced later without
  redrawing. Saving creates a subfolder named after the site (whatever you
  typed in "Site name") under whichever parent folder you pick via the
  sidebar's "Browse" button, so multiple sites stay separated and easy to
  find under one shared parent folder. Loading just points back at that
  site's own subfolder.
- `modules/fetch.py` - queries DEA's STAC catalogue and loads scenes for the
  drawn ROI, using the vendored `vendor/rs_data.py` and
  `vendor/rs_processing.py`. Can cache fetched scenes as GeoTIFFs under
  `data_cache/` (created on first run), but does not by default - see
  "Raster caching is opt-in" below.
- `vendor/` - self-contained copies of the code this app depends on (see
  `vendor/README.md`), so this folder doesn't need anything else alongside
  it to run.
- `modules/aggregate.py` - builds the results table, prefers Sentinel-2 over
  Landsat on shared dates, and computes the mean-monthly proportion-closed
  statistic (equal-weighted across calendar months, to correct for uneven
  survey frequency).
- `config/products.json` - two DEA product definitions used by this app:
  `landsat_full` (Landsat 5/7/8/9, 30 m) and `sentinel_full` (Sentinel-2,
  10 m), each spanning the full available archive for that sensor.
- `data_cache/` - cached rasters per site/sensor/date (created on first run,
  fixed location - unlike the site shapefiles, this is just a working cache
  rather than something you'd want to file away by hand).

**Raster caching is opt-in, not required for analysis.** The connectivity
check only ever looks at each scene's raster while it's in memory during the
"Run analysis" loop - it never reads back from disk. So writing every
fetched scene to `data_cache/` during a run was only ever a convenience for
the scene-preview feature, not something the analysis itself needs, and it's
what was filling up the folder on large date ranges. The "Cache every
scene's raster during this run" checkbox on the run tab (off by default)
controls this. With it off, clicking a point in the results plot fetches
just that one scene from DEA on demand (shown with a spinner) rather than
requiring it to already be cached - a bit slower the first time you preview
a given scene, but nothing is written to disk unless you ask for it. The
sidebar's "Raster cache" section shows how much space `data_cache/` is
using and has a "Clear raster cache" button to empty it at any time -
nothing is lost by clearing it, since scenes are always re-fetchable from
DEA.

## Design decisions worth knowing about

**Open/closed combination rule.** The R script keeps the NDWI-based and
fmask-based connectivity checks as two separate columns for comparison. Per
the spec for this app, they're combined into one status: **open** if either
method finds a path, **closed** if neither does and nothing is blocking the
view, **indeterminate** otherwise. Both individual results are still kept
in the results table if you want to check them.

**Scene preview instead of a true georeferenced map overlay.** "Click a
point, see the raster" is implemented as an NDWI heatmap with the
inside/outside lines overlaid in the correct pixel positions - not a
reprojected image layered back onto the satellite basemap. This is enough
to sanity-check that a given date's classification looks right, without
the extra reprojection/bounds handling a full map overlay would need.

**Scenes must (by default) fully cover the drawn ROI.** Before analysing,
scenes are filtered to those covering >= 99.9% of the ROI polygon (via
`filter_stac_items_region_overlap`), which drops dates where the ROI
straddles two tiles collected on different days or sits at the edge of a
swath - these otherwise just leave part of the ROI as nodata and usually
come out indeterminate anyway. This can be turned off with the checkbox on
the run tab if you'd rather see every scene regardless of coverage.

**Cloud-cover filter is scene-level, not ROI-level.** `eo:cloud_cover` is the
whole-scene's cloud percentage, not the percentage over just your drawn
ROI. A scene can pass this filter while still being locally cloudy over
your specific region - the "indeterminate" classification and the
cloud/no-data mask overlay in the scene preview are there to catch that
case.

**Confirmed layers show a persistent state.** Each of the region/lines/
structures tabs now switches to a read-only "confirmed" view (with a
Redraw button) once you confirm that layer, instead of leaving the same
draw controls/buttons on screen with no visible change.

**Theme.** `.streamlit/config.toml` sets a pastel light-blue theme for the
app chrome; map layers and plot markers use a matching pastel palette
(defined once as `PASTEL` near the top of `app.py`) - light blue for the
ROI/Landsat/inside line, pastel rose for the outside line/Sentinel-2,
pastel peach for structures.

**Cloud/no-data mask in the scene preview.** A checkbox (on by default)
overlays which pixels are no-data, cloud, cloud shadow, or outside the
drawn ROI - the same categories that drive the indeterminate classification
- so you can see at a glance why a given scene came out indeterminate.

**Plot method selector.** A radio above the time series plot switches
between the combined status (default - open if either method connects),
NDWI only, and fmask only. The summary metrics (open/closed/indeterminate
counts, mean monthly % closed) switch to match, so the numbers on screen
always describe whichever one is selected.

**NDWI/fmask background toggle in the scene preview.** A "Background" radio
switches the scene preview between the continuous NDWI heatmap (default)
and a categorical view of the raw oa_fmask classes (water, land, cloud,
cloud shadow, snow-treated-as-water, no-data, outside the drawn ROI) -
the actual data behind the fmask connectivity method, parallel to how NDWI
is the data behind the NDWI method. The cloud/no-data mask overlay checkbox
only applies to the NDWI background, since the fmask background already
shows those classes directly.

**Connectivity diagnostic in the scene preview.** A "Show connectivity
diagnostic" checkbox recomputes the chosen scene's NDWI or fmask check live
and shows exactly which patches the *optimistic* pass (cloud/no-data
assumed water) found reaching the inside line, the outside line, or both.
If a result looks surprising (e.g. "closed" on a heavily clouded scene),
this shows the actual computation behind it rather than requiring an
eyeball judgement from the raster image alone.

**Duplicate same-date tiles are resolved by picking the better-covered one.**
A single calendar date can have more than one DEA STAC item - most often two
adjacent tiles from the same overpass, captured a few seconds apart with
distinct timestamps, where the ROI happens to sit near the tile boundary.
Both `run_site_analysis()` and `fetch_single_scene()` keep only the
best-covered scene per date (fewest no-data cells / highest valid-pixel
fraction) when this happens, so a near-empty tile can't end up in the
results table or scene preview in place of the good one.

**On-demand scene fetch only accepts an exact date match.** If DEA has no
item exactly on the requested date even after widening the search by a day
either side, `fetch_single_scene()` raises a clear error rather than
silently falling back to whatever the nearest returned scene happened to
be - this avoids rendering a preview from a different, barely-overlapping
tile on a neighbouring date, which would otherwise show up as an
unexplained, mostly-grey (no-data) image. This error is rare and usually
points to a timezone/date-boundary edge case right around midnight UTC.

**GeoTIFFs are written directly rather than through a shared helper.**
`fetch.py` computes the clipped, processed data for each scene and writes
its own GeoTIFFs band-by-band, rather than relying on a generic
xarray-to-raster conversion step. This keeps scene writing self-contained
and avoids assumptions about array shape that a more generic helper would
need to handle.
