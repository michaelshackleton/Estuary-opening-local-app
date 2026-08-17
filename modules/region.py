"""
Manages the three user-drawn layers for a site (ROI polygon, inside/outside
lines, optional structure polygons), including saving/loading them as Esri
Shapefiles - the same format the existing R script reads (`*_lines.shp`,
`*structures*.shp`) - so an analysis can be reproduced later without
redrawing, and so these layers can be opened directly by the R script or
any GIS if needed.

The user picks the folder each time (via a native folder-browse dialog in
the app) rather than layers being saved to one fixed location - save()/
load() below just read/write whatever folder they're given.

Layers are stored in EPSG:4326 (lat/lon, what the Leaflet draw tools return)
and reprojected to a local UTM zone on demand for analysis - the UTM zone is
auto-detected from the ROI centroid so this works anywhere in Australia
without the user having to know their MGA zone.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

import geopandas as gpd
from shapely.geometry import shape

WGS84 = "EPSG:4326"


def auto_utm_epsg(lon: float, lat: float) -> int:
    """WGS84 UTM zone EPSG code for a given lon/lat. Australia is entirely
    southern hemisphere, but this works globally for robustness."""
    zone = int((lon + 180) // 6) + 1
    return (32700 if lat < 0 else 32600) + zone


@dataclass
class SiteLayers:
    name: str
    roi: gpd.GeoDataFrame  # single polygon, EPSG:4326
    lines: gpd.GeoDataFrame  # two lines with a 'position' column: inside/outside, EPSG:4326
    structures: Optional[gpd.GeoDataFrame] = None  # optional polygons, EPSG:4326

    # -- validation ---------------------------------------------------
    def validate(self) -> list[str]:
        """Returns a list of human-readable problems, empty if valid."""
        problems = []
        if self.roi is None or len(self.roi) == 0:
            problems.append("No region-of-interest polygon has been drawn yet.")
        elif len(self.roi) > 1:
            problems.append(
                f"Region of interest has {len(self.roi)} polygons - only one is expected. "
                "Using the first one."
            )
        if self.lines is None or len(self.lines) == 0:
            problems.append("No inside/outside lines have been drawn yet.")
        else:
            if "position" not in self.lines.columns:
                problems.append("Lines layer is missing a 'position' column.")
            else:
                positions = self.lines["position"].tolist()
                if positions.count("inside") != 1:
                    problems.append("Need exactly one line labelled 'inside'.")
                if positions.count("outside") != 1:
                    problems.append("Need exactly one line labelled 'outside'.")
        return problems

    # -- geometry access ------------------------------------------------
    def target_crs(self) -> int:
        """Auto-detected UTM EPSG code from the ROI centroid."""
        centroid = self.roi.to_crs(WGS84).geometry.iloc[0].centroid
        return auto_utm_epsg(centroid.x, centroid.y)

    def inside_line(self, target_crs=None) -> gpd.GeoDataFrame:
        gdf = self.lines[self.lines["position"] == "inside"]
        return gdf.to_crs(target_crs) if target_crs else gdf

    def outside_line(self, target_crs=None) -> gpd.GeoDataFrame:
        gdf = self.lines[self.lines["position"] == "outside"]
        return gdf.to_crs(target_crs) if target_crs else gdf

    def roi_polygon(self, target_crs=None):
        gdf = self.roi.to_crs(target_crs) if target_crs else self.roi
        return gdf.iloc[0].geometry

    def structures_reprojected(self, target_crs) -> Optional[gpd.GeoDataFrame]:
        if self.structures is None or len(self.structures) == 0:
            return None
        return self.structures.to_crs(target_crs)

    # -- save / load ------------------------------------------------------
    # Filenames are fixed within whatever folder the user picks, following
    # the same convention the R script's `find_structures_file()` and the
    # `*_lines.shp` files already use in this repo's `data/` folders.
    ROI_FILE = "roi.shp"
    LINES_FILE = "lines.shp"
    STRUCTURES_FILE = "structures.shp"

    def save(self, parent_folder: str) -> str:
        """Creates a subfolder named after this site (self.name) inside
        `parent_folder`, and writes roi.shp / lines.shp / (optionally)
        structures.shp into it. The user chooses `parent_folder` via the
        app's folder-browse dialog - keeping one parent folder for all
        sites (each in its own site-name subfolder) keeps them separate
        and easy to find again. Returns the site's own folder path."""
        folder = os.path.join(parent_folder, self.name)
        os.makedirs(folder, exist_ok=True)
        self.roi.to_file(os.path.join(folder, self.ROI_FILE), driver="ESRI Shapefile")
        self.lines.to_file(os.path.join(folder, self.LINES_FILE), driver="ESRI Shapefile")
        struct_path = os.path.join(folder, self.STRUCTURES_FILE)
        if self.structures is not None and len(self.structures) > 0:
            self.structures.to_file(struct_path, driver="ESRI Shapefile")
        else:
            # remove a stale structures shapefile (and its sidecar files)
            # left over from a previous save of this same folder
            for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
                stale = os.path.join(folder, "structures" + ext)
                if os.path.exists(stale):
                    os.remove(stale)
        return folder

    @classmethod
    def load(cls, folder: str) -> "SiteLayers":
        """Reads roi.shp / lines.shp / (optionally) structures.shp from
        `folder`, which the user picked via the app's folder-browse
        dialog. `name` is derived from the folder's own name."""
        roi_path = os.path.join(folder, cls.ROI_FILE)
        lines_path = os.path.join(folder, cls.LINES_FILE)
        if not os.path.exists(roi_path) or not os.path.exists(lines_path):
            raise FileNotFoundError(
                f"'{folder}' doesn't contain both {cls.ROI_FILE} and {cls.LINES_FILE} - "
                "is this the right folder?"
            )
        roi = gpd.read_file(roi_path)
        lines = gpd.read_file(lines_path)
        struct_path = os.path.join(folder, cls.STRUCTURES_FILE)
        structures = gpd.read_file(struct_path) if os.path.exists(struct_path) else None
        name = os.path.basename(os.path.normpath(folder))
        return cls(name=name, roi=roi, lines=lines, structures=structures)


# --------------------------------------------------------------------------
# Helpers for converting the raw GeoJSON coming back from the Leaflet draw
# control (via streamlit-folium) into GeoDataFrames
# --------------------------------------------------------------------------

def geojson_features_to_gdf(features: list[dict], crs=WGS84) -> gpd.GeoDataFrame:
    """`features` is a list of GeoJSON Feature dicts, as returned in
    st_folium's 'all_drawings' list."""
    geoms = [shape(f["geometry"]) for f in features]
    props = [f.get("properties", {}) or {} for f in features]
    gdf = gpd.GeoDataFrame(props, geometry=geoms, crs=crs)
    return gdf
