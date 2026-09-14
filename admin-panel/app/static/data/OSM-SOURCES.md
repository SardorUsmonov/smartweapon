# OpenStreetMap data used by the executive map

Retrieved 2026-09-14. Data © OpenStreetMap contributors, licensed under ODbL 1.0: https://www.openstreetmap.org/copyright

- `uzbekistan-osm.geojson`: Uzbekistan administrative boundary, OSM relation 196240. Retrieved once through Nominatim Lookup as GeoJSON, with `polygon_geojson=1` and `polygon_threshold=0.005`. Multipolygon rings, enclaves and holes are retained. The simplified boundary is for the overview, not a cadastral or legal boundary determination.
  Source: https://www.openstreetmap.org/relation/196240
  Lookup: https://nominatim.openstreetmap.org/lookup?osm_ids=R196240&format=geojson&polygon_geojson=1&polygon_threshold=0.005&accept-language=uz
- `uz-regions-osm.json`: representative region label points from one Nominatim batch lookup of the 14 subarea relations belonging to relation 196240. Each `osm_id` identifies its source at `https://www.openstreetmap.org/relation/{osm_id}`. Existing application region codes are matched by region name. These are regional aggregate markers, not locations of facilities, equipment or people. All 14 points were checked to fall inside the country geometry.

Both data files are served locally. No geocoding API is called by the dashboard. Application counts and drill-down permissions come from the existing scoped server-rendered SVG, not from OpenStreetMap.

The background now uses the official vector endpoint `https://vector.openstreetmap.org/shortbread_v1/{z}/{x}/{y}.mvt`, with visible attribution. TileJSON: https://vector.openstreetmap.org/shortbread_v1/tilejson.json. The source provides native zooms 0–14; the overview uses native zoom 6 or higher to keep main roads visible, with overzoom above 14. Local canvas rendering draws land, water, roads, buildings and administrative region lines. Labels embedded in the raster version are no longer used: region names are separate HTML elements above the clipped geometry, so they are not cut at country boundaries.

Tiles require an internet connection. Only the current viewport is requested; there is no bulk downloader, offline tile archive, or proxy. Browser HTTP caching is respected. Decoded geometry exists only with its visible tile canvases, so theme changes can repaint without downloading again. The request-specific `strict-origin-when-cross-origin` referrer policy supplies the truthful application origin required by OSM without sending page paths, query strings or preview capability tokens. General application security headers are unchanged.

Vector tile usage policy: https://operations.osmfoundation.org/policies/vector/
Leaflet 1.9.4 is vendored under `../vendor/leaflet/` with its BSD-2-Clause license. Its code and CSS were obtained from the published Leaflet package; see https://leafletjs.com/download.html.

MVT decoder libraries and their licenses are documented in `../vendor/osm-vector/SOURCES.md` (pbf 4.0.2 and @mapbox/vector-tile 2.0.5). These are served locally and do not contact a CDN at runtime.
