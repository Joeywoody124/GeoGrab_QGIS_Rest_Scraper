# SC GIS Data Scraper for QGIS - Project Brainstorm
## Project: Rest_Scraper_QGIS
## Date: 2025-02-05

---

## Vision

A polished, professional QGIS plugin-style tool that automatically discovers
and downloads GIS data from ArcGIS REST services based on where the user is
working. Built for South Carolina municipal/county engineering consulting but
extensible to any state.

The killer feature: **drop a polygon or zoom to an area, and the tool
automatically finds what REST services cover that location and what layers
are available** -- parcels, flood zones, zoning, roads, utilities, aerials.

---

## Feature Tiers

### TIER 1 - Core (Build First, Get It Working)
- [x] Basic REST service connection and layer browsing
- [x] OID-paginated feature download
- [x] Spatial filter by polygon layer or map extent
- [x] GeoPackage output with auto-add to map
- [ ] **SC Service Registry** - JSON catalog of known SC REST endpoints
  - Berkeley County GIS Consortium
  - Charleston County / City of Charleston
  - Dorchester County
  - Mount Pleasant
  - FEMA NFHL
  - SCDOT
  - SCGIC
  - SCDNR
  - USGS National Map
- [ ] **Region Picker** - dropdown to select county/municipality
  - Auto-populates available services for that area
  - Shows service health status (green/yellow/red)
- [ ] **Clean, professional tabbed GUI**
  - Tab 1: Quick Download (region picker + common layers)
  - Tab 2: Custom URL (paste any REST URL)
  - Tab 3: Service Browser (full layer tree)

### TIER 2 - Smart Features (The Wow Factor)
- [ ] **Auto-Detect Location** - reads CRS + extent of active layers
  - Determines which SC county the project is in
  - Auto-suggests relevant services
  - "You appear to be working in Berkeley County. Load parcels?"
- [ ] **Common Layer Presets** for engineering consulting:
  - "Parcels" - finds parcel layer from best available source
  - "Flood Zones" - FEMA NFHL S_Fld_Haz_Ar
  - "Roads" - SCDOT or local
  - "Zoning" - municipal source
  - "Contours" - county or state
  - "Aerial Imagery" - as WMS/WMTS tile layer
- [ ] **Service Health Monitor** - pings endpoints on connect
  - Caches results so repeated checks are fast
  - Falls back to alternate sources when primary is down
- [ ] **Download Queue** - check multiple layers, download all at once
  - Progress bar per layer
  - Summary report when complete

### TIER 3 - Polish (GitHub-Ready)
- [ ] **Custom URL Manager** - save/edit/delete custom REST URLs
  - Persists to JSON config file
  - Import/export for sharing between machines
- [ ] **Download History Log** - tracks what was downloaded, when, from where
  - Useful for deliverable documentation
  - "Data sourced from Berkeley County GIS, downloaded 2025-02-05"
- [ ] **Settings Panel**
  - Default output directory
  - Default CRS for downloads
  - Batch size (for slow connections)
  - SSL verification toggle
  - Proxy settings
- [ ] README.md with screenshots
- [ ] Installation instructions
- [ ] License (MIT)

---

## Architecture

```
Rest_Scraper_QGIS/
    README.md
    LICENSE
    sc_rest_scraper/
        __init__.py              # Package init
        main.py                  # Entry point, dialog launcher
        gui/
            __init__.py
            main_dialog.py       # Main tabbed window
            widgets.py           # Reusable widget components
            styles.py            # QSS stylesheet for theming
        core/
            __init__.py
            downloader.py        # REST fetch, pagination, conversion
            service_registry.py  # SC service catalog management
            location_detect.py   # Auto-detect county from layers
            health_check.py      # Service ping/status
        config/
            sc_services.json     # South Carolina service catalog
            user_services.json   # User-added custom URLs
            settings.json        # User preferences
        resources/
            icons/               # Tool icons
            sc_counties.geojson  # County boundaries for detection
    docs/
        PROJECT_BRAINSTORM.md
        CHANGELOG.md
    launcher.py                  # exec(open()) launcher for QGIS
```

---

## SC Service Registry Design

The JSON catalog is the backbone. Example structure:

```json
{
  "regions": {
    "berkeley_county": {
      "name": "Berkeley County",
      "fips": "45015",
      "bbox": [-80.45, 32.90, -79.55, 33.55],
      "services": [
        {
          "name": "Berkeley County GIS - Desktop",
          "url": "https://gis.berkeleycountysc.gov/arcgis/rest/services/desktop/internet_map/MapServer",
          "type": "MapServer",
          "common_layers": {
            "parcels": {"id": 5, "name": "Parcels"},
            "zoning": {"id": 12, "name": "Zoning"},
            "roads": {"id": 20, "name": "Street Centerlines"}
          },
          "notes": "Primary source. Updated weekly."
        }
      ]
    }
  },
  "statewide": [
    {
      "name": "FEMA NFHL",
      "url": "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer",
      "common_layers": {
        "flood_zones": {"id": 28, "name": "S_Fld_Haz_Ar"}
      }
    },
    {
      "name": "SCDOT",
      "url": "https://services1.arcgis.com/VaY7cY9pvUYUP1Lf/arcgis/rest/services"
    }
  ]
}
```

---

## Auto-Detect Logic

1. Get all loaded vector layers
2. Check their CRS -- if SC State Plane (EPSG:2273 or 6570), strong SC signal
3. Get combined bounding box of all layers
4. Transform bbox to WGS84
5. Compare against county bbox entries in sc_services.json
6. If match found, suggest that county's services
7. If ambiguous (near county border), offer multiple options

---

## GUI Design Concept

### Tab 1: "Quick Download"
```
+--------------------------------------------------+
|  [Auto-detected: Berkeley County]  [Refresh]     |
|                                                   |
|  Available Data:                                  |
|  [x] Parcels          [Berkeley County GIS]      |
|  [ ] Flood Zones      [FEMA NFHL]               |
|  [ ] Zoning           [Berkeley County GIS]      |
|  [ ] Roads            [SCDOT]                    |
|  [ ] Contours         [Berkeley County GIS]      |
|                                                   |
|  Clip to: [Basin_Boundary_v  ]  Buffer: [500 ft] |
|  Output:  [E:\Projects\G-Town\data\   ] [...]    |
|                                                   |
|  [ Download Selected ]              [x] Add to map|
+--------------------------------------------------+
```

### Tab 2: "Custom URL"
```
+--------------------------------------------------+
|  Service URL: [paste any REST URL here       ] [Go]|
|                                                   |
|  Layers:                                          |
|  +-- Group: Administrative                        |
|  |   [x] [5] Parcels                             |
|  |   [ ] [6] Municipal Boundaries                |
|  +-- Group: Environmental                         |
|  |   [ ] [12] Wetlands                           |
|                                                   |
|  [Save to My Services]  [Download Selected]       |
+--------------------------------------------------+
```

### Tab 3: "My Services"
```
+--------------------------------------------------+
|  Saved Services:                                  |
|  > Berkeley County GIS          [Edit] [Delete]  |
|  > Charleston County            [Edit] [Delete]  |
|  > Mount Pleasant               [Edit] [Delete]  |
|  > FEMA NFHL                    [Edit] [Delete]  |
|                                                   |
|  [Add New]  [Import JSON]  [Export JSON]         |
+--------------------------------------------------+
```

---

## Priority Evaluation for Your Workflow

Based on your typical project pattern:

1. **You get a project area** (drainage basin, study area polygon)
2. **You need base data** (parcels, flood zones, roads, zoning, aerials)
3. **You're often in the SC Lowcountry** (Berkeley, Charleston, Dorchester)
4. **County REST services go down intermittently**
5. **You work across multiple counties** for different clients

The HIGHEST VALUE features are:
- Auto-detect county from project layers (saves time every project)
- Common layer presets (one-click "get me parcels")
- Service health fallback (Berkeley down? Try alternate endpoint)
- Download history for deliverable documentation

---

## Implementation Plan

### Phase 1: Foundation (This Session)
- Project structure and file scaffold
- SC service registry JSON with verified URLs
- Core downloader module (extract from v2 script)
- Basic tabbed GUI shell

### Phase 2: Smart Features (Next Session)
- Auto-detect location logic
- Common layer presets
- Service health checking
- Download queue

### Phase 3: Polish (GitHub Release)
- Custom URL manager with persistence
- Download history/logging
- Settings panel
- README, screenshots, license
- GitHub repo setup

---

## Name Ideas
- **SC REST Scraper** (descriptive)
- **GeoGrab** (catchy)
- **DataHarvester** (professional)
- **LayerFetch** (clean)
- **SC GIS Toolbox** (boring but clear)
- **RestPull** (short)
