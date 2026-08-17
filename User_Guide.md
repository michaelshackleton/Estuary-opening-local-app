# Estuary Mouth Monitor — User Guide

This app lets you draw a region around an estuary on a satellite map, mark where the river and ocean sides of the mouth are, and automatically check every available Landsat and Sentinel-2 satellite image for that area to work out whether the mouth was open or closed over time.

It runs entirely on your own computer as a local web app — no data is uploaded anywhere except the normal requests to Digital Earth Australia's servers to fetch the satellite imagery.

## 1. Installing it (one-off setup)

You'll need Python installed on the computer (3.10 or newer). To check, open Command Prompt and type `python --version`.

1. Open Command Prompt (search for "cmd" in the Start menu).
2. Navigate to the app folder. If it was saved to, for example, `C:\Users\YourName\Documents\rs-utils-main\Claude_script`, type:
   ```
   cd "C:\Users\YourName\Documents\rs-utils-main\Claude_script"
   ```
3. Create a Python environment just for this app (keeps its packages separate from anything else on the computer):
   ```
   python -m venv .venv
   ```
4. Activate it:
   ```
   .venv\Scripts\activate
   ```
   You'll know it worked if the prompt now starts with `(.venv)`.
5. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
   This can take several minutes — some of the packages (satellite image handling libraries) are large.

You only need to do this once. If the install fails partway through, copy the error message — some of these packages occasionally need a specific fix depending on the Python version installed.

## 2. Starting the app

Every time after that, just double-click **`run_app.bat`** in the app folder. A browser window should open automatically showing the app. If it doesn't open by itself, the Command Prompt window it launches will show a web address (something like `http://localhost:8501`) — copy that into a browser.

Leave the Command Prompt window open while using the app; closing it shuts the app down. To stop the app, close that window or press `Ctrl+C` in it.

## 3. Using the app

The app is organised into a sidebar (site name and save/load) and four tabs that you work through in order.

### Site name (sidebar)

Give the site a short name (e.g. `Barwon_estuary`) at the top of the sidebar before you start drawing — this is used as the filename when you save your work later.

### Tab 1 — Region of interest

Draw a boundary around the estuary mouth area you want to analyse:

1. On the satellite map, use the polygon tool (top-left corner of the map) to click out a boundary around the estuary. Double-click to finish the shape.
2. Click **Confirm ROI**.
3. The tab will switch to a read-only view showing your confirmed region with a green tick. Click **Redraw ROI** at any point if you want to start over.

This region defines the area satellite images are fetched for, so keep it reasonably tight around the estuary mouth rather than the whole waterway — smaller regions mean faster runs.

### Tab 2 — Inside / outside lines

This defines the two "gates" the app checks for a connected water path between:

1. Use the polyline tool to draw **two** lines: one crossing the river on the **inland side** of the mouth, and one crossing the ocean on the **seaward side**.
2. Once both lines are drawn, a dropdown appears under the map for each one — set one to **inside** and the other to **outside**.
3. Click **Confirm lines**.

### Tab 3 — Structures (optional)

If there's a bridge, causeway, or similar structure crossing the estuary that would otherwise block the satellite's view of the water underneath it, draw a polygon over it here so the app knows to treat those pixels as passable water rather than land. If there's nothing to add, just click **No structures at this site**.

### Tab 4 — Run & results

1. Set the **date range** (defaults to the full Landsat archive, back to 1985) and the **maximum cloud cover** you'll accept per image (default 20%).
2. Leave **"Only use scenes that fully cover the drawn region"** checked unless you specifically want every available image regardless of coverage gaps — this is on by default because partial-coverage scenes mostly just come out as unusable anyway, and skipping them makes the run faster.
3. Click **Run analysis**. A progress bar shows what's being fetched and processed — this can take anywhere from a couple of minutes to a while longer depending on the size of the region and date range.

Once it finishes, you'll see:

- **Summary numbers**: how many scenes came out open, closed, or indeterminate, and the mean monthly percentage of time closed (this is averaged by calendar month first, so periods with more frequent satellite coverage — mainly after Sentinel-2 launched in 2015 — don't skew the result).
- **"Classify using"**: a switch above the plot to view the combined result (open if either method finds a path — the default), or just the NDWI or fmask method on its own.
- **The time series plot**: each point is one satellite image, plotted by date, coloured/shaped by whether it came from Landsat or Sentinel-2. **Click any point** to load that image below for a closer look.
- **Download results as CSV**: exports the full results table for use elsewhere (Excel, R, etc).

#### Scene preview

After clicking a point on the plot, the image loads below with a few options:

- **Background**: switch between the NDWI index (a continuous water-likelihood measure) or the satellite's own raw cloud/water classification (fmask), shown as flat colour categories.
- **Show cloud / no-data mask overlay** (NDWI view only): highlights which pixels were cloud, no-data, or outside your drawn region — the pixels that can cause an "indeterminate" result.
- **Show connectivity diagnostic**: for double-checking a surprising result. It recomputes the check live and colours the map to show exactly which areas the algorithm found connected to the inside line, the outside line, or both — if you can't tell by eye whether a path should exist through the cloud, this shows you definitively what the algorithm actually found.

### Saving and reloading a site

Rather than redrawing everything each time, you can save your region/lines/structures and load them again later:

- **Save**: enter a site name in the sidebar, choose (or type) a parent folder using the **Browse** button next to "Parent folder", then click **Save current site layers**. This creates a subfolder named after your site inside that parent folder, so multiple sites stay organised together.
- **Load**: browse to that site's own subfolder using the **Browse** button next to "Load folder", then click **Load site layers**.

These are saved as standard Esri Shapefiles, so they can also be opened directly in GIS software or the original R script if needed.

## Troubleshooting

- **The app won't start / errors about a missing module**: make sure you activated the environment first (`.venv\Scripts\activate`) before running anything manually, or just use `run_app.bat`, which does this automatically. If it names a specific missing package, run `pip install <package name>` with the environment activated.
- **A folder-browse button doesn't open anything**: type the folder path directly into the text box next to it instead — the Browse button is just a shortcut.
- **A run is taking a long time**: larger regions and longer date ranges naturally take longer. Narrowing the region to just the estuary mouth, shortening the date range, or lowering the cloud-cover threshold will speed things up.
- **Anything else**: note the exact error message shown on screen — that's the fastest way to get it fixed.
