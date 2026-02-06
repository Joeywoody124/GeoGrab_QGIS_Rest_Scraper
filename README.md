# GeoGrab - ArcGIS REST Data Downloader for QGIS

**Auto-detect your project location. One-click download of parcels, flood zones, roads, zoning, and more from ArcGIS REST services into GeoPackage format.**

![QGIS](https://img.shields.io/badge/QGIS-3.40+-3aaa35.svg?logo=qgis&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB.svg?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Version](https://img.shields.io/badge/version-1.5.0-0288d1.svg)

---

## Overview

GeoGrab is a QGIS Python tool that analyzes your loaded layers to determine where you're working, then matches that location to a registry of known ArcGIS REST services. Instead of hunting for URLs, pasting them into a browser, figuring out layer IDs, and writing query strings, you check a few boxes and click download.

It was built for municipal and county engineering consulting in the SE United States, but the Custom URL tab and service bookmark system make it usable with any public ArcGIS REST endpoint.

**No plugins to install. No pip packages. Just clone, point the launcher at it, and go.**

---

## How It Works

```
Your QGIS Project                    GeoGrab
   |                                    |
   |-- Canvas center + CRS ----------> Auto-detect region
   |   (fallback: layer extents)        |
   |                                    |--> Match to service registry
   |                                    |     (sc_services.json)
   |                                    |
   |                                    |--> Show available layers
   |                                    |     with checkboxes
   |                                    |
   |   <-- Download to .gpkg ---------- |--> OID-paginated REST queries
   |   <-- Add to map canvas            |     with spatial filtering
```

Detection uses canvas center point as the primary method (best for zoomed-in views), with layer-extent bounding box overlap as a fallback. CRS analysis checks for SC/NC State Plane families as a confidence booster.

---

## Features

**Auto-Detection**
- Canvas-center detection (primary) with layer-extent fallback
- Supports SC State Plane (EPSG:2273, 3361) and NC State Plane (EPSG:2264, 3358, 6543) families
- Confidence scoring: HIGH / MEDIUM / LOW with manual override dropdown

**Three-Tab Interface**
- **Quick Download**: Pre-configured layers for your detected region with engineering presets (Drainage Study, Site Assessment, Infrastructure Inventory)
- **Custom URL**: Paste any ArcGIS REST MapServer or FeatureServer URL, browse layers, check what you want
- **My Services**: Persistent bookmarks with saved layer selections that survive between sessions

**Browse All Layers with Directory Crawling**
- Expandable panel on the Quick Download tab lists every service for your region
- Direct MapServer/FeatureServer entries connect to list feature layers
- ServiceDirectory entries (like SCDOT with hundreds of datasets) auto-crawl to show child services in a secondary dropdown, then connect to whichever one you pick
- Non-browsable service types (WebApp, Portal, OpenDataHub, ImageServer) are filtered out automatically

**Download Engine**
- OID-based pagination handles datasets of any size without hitting MaxRecordCount limits
- Spatial filtering by map canvas extent or polygon clip layer with configurable buffer
- ESRI JSON to QGIS geometry conversion (Point, MultiLineString, MultiPolygon)
- GeoPackage export with multi-layer append (multiple downloads into one .gpkg)
- Automatic map canvas loading after download

**Safety Guardrails**
- Pre-flight feature count query before every download
- Extent area validation prevents accidentally downloading entire states
- Density-aware thresholds tighten for parcels, contours, and other heavy layers
- Configurable warning (10K features) and hard block (100K features) limits
- No-spatial-filter protection blocks full-service dumps

**Sketch Theme**
- Light, warm, paper-like interface with pencil-black text and blue accents
- Medium and Dark themes available in `styles.py`

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/Joeywoody124/GeoGrab_QGIS_Rest_Scraper.git
```

### 2. Update the Launcher Path

Open `launcher.py` and set `PROJECT_ROOT` to your local clone path:

```python
PROJECT_ROOT = r'E:\path\to\GeoGrab_QGIS_Rest_Scraper'
```

### 3. Launch in QGIS

Open the QGIS Python Console (`Ctrl+Alt+P`) and run:

```python
exec(open(r'E:\path\to\GeoGrab_QGIS_Rest_Scraper\launcher.py', encoding='utf-8').read())
```

GeoGrab opens, detects your region, and populates available layers. Check what you need, pick an output path, and hit **Download Selected**.

The launcher automatically cleans `__pycache__` folders on each run, so code changes take effect immediately without manual cleanup.

---

## Pre-Configured Service Registry

### Regions (11)

| Region | State | Quick Download Layers | Service Type |
|--------|-------|----------------------|--------------|
| Berkeley County | SC | Parcels, Zoning, Roads, Contours, Flood Zones, Addresses, Boundaries | MapServer (bundled, hardcoded IDs) |
| Beaufort County | SC | All 8 layer types mapped | MapServer (separate per dataset) |
| Charleston County | SC | Parcels, Addresses, Roads, Buildings | MapServer |
| Dorchester County | SC | Parcels | MapServer |
| Georgetown County | SC | Parcels (EPSG:3361 native) | MapServer (Portal) |
| Town of Bluffton | SC | Zoning, Contours, Boundaries, Flood | FeatureServer (ArcGIS Online, 60+ datasets) |
| Mount Pleasant | SC | Browse via directory crawl | ServiceDirectory |
| Jasper County | SC | No REST endpoint | qPublic web app |
| North Charleston | SC | Uses Charleston County services | ArcGIS Enterprise Portal |
| McDowell County | NC | Addresses, Contours, Roads, Parcels, City Limits | MapServer (WebGIS) |
| Buncombe County | NC | Property, Streets, Addresses | MapServer (65+ layers) |

### Statewide and Federal Services (11)

| Service | Coverage | Type | Category |
|---------|----------|------|----------|
| FEMA NFHL | National | MapServer | Flood zones, FIRM panels, BFEs, cross sections |
| SCDOT | SC | ServiceDirectory | Roads, bridges, traffic, pavement (crawlable) |
| SCGIC | SC | ServiceDirectory | General statewide data (crawlable) |
| SCDNR | SC | ServiceDirectory | Wildlife, waterways, public lands (crawlable) |
| SCDNR Open Data Hub | SC | OpenDataHub | Downloadable shapefiles and features |
| SCDHEC / SCDES | SC | ServiceDirectory | Environmental and health data (may 403) |
| NC OneMap | NC | ServiceDirectory | Statewide NC data (may need auth) |
| USGS Government Units | National | MapServer | County and municipal boundaries |
| USGS NHD | National | MapServer | Hydrography and watersheds |
| USGS 3DEP | National | ImageServer | Elevation data |

---

## Safety System

Downloads are checked before they start:

| Check | Warning | Block |
|-------|---------|-------|
| Feature count | 10,000 | 100,000 |
| Extent area | ~1,000 sq mi | ~8,000 sq mi |
| Dense layers at broad extent | 5,000 | 50,000 |
| No spatial filter | -- | Always blocked |

Warning dialogs show feature count, estimated file size, and query area. All thresholds are configurable in `core/safety.py`.

---

## Persistent Service Bookmarks

The My Services tab stores your custom service connections and layer selections between sessions:

1. **Custom URL tab**: Paste a REST URL, click Connect, check the layers you want
2. **Save to My Services**: Names the bookmark and stores URL + checked layers
3. **My Services tab**: Click a saved service to see layers with previous selections restored
4. **Refresh**: Reconnects to the service and preserves your check states
5. **Download**: Works the same as Quick Download, just from your bookmarks

Bookmarks are stored in `config/user_services.json` and persist across QGIS sessions.

---

## Project Structure

```
GeoGrab_QGIS_Rest_Scraper/
    launcher.py                          # Run this in QGIS Python Console
    README.md
    CHANGELOG.md
    CONTRIBUTING.md
    LICENSE
    .gitignore
    sc_rest_scraper/
        __init__.py                      # Package version (1.5.0)
        core/
            downloader.py                # REST engine: fetch, paginate, convert, export
            location_detect.py           # Auto-detect region from canvas + CRS
            safety.py                    # Pre-flight download guardrails
        gui/
            main_dialog.py               # Three-tab GUI with browse-all + directory crawl
            styles.py                    # Sketch/Medium/Dark theme stylesheets
        config/
            sc_services.json             # Service registry (11 regions + statewide)
            user_services.json           # User bookmarks (per-machine, git-ignored)
    docs/
        HANDOFF.md                       # Session continuity notes (git-ignored)
        PROJECT_BRAINSTORM.md            # Original feature planning
```

---

## Adding a Region

Edit `sc_services.json` following the pattern of existing entries. Key fields:

- **`bbox_wgs84`**: `[xmin, ymin, xmax, ymax]` in WGS84 for auto-detection
- **`known_layers`**: Maps standard type keys (`parcels`, `zoning`, `roads`, etc.) to service-specific layer names and IDs
- **`id`**: Hard-coded layer ID (preferred). Use `id_hint` for substring matching only as a fallback.
- **`type`**: Service type determines how GeoGrab handles the entry: `MapServer`/`FeatureServer` (direct browse), `ServiceDirectory` (directory crawl), or `WebApp`/`Portal`/`OpenDataHub`/`ImageServer` (filtered out of browse)

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full walkthrough.

---

## Requirements

- **QGIS 3.40+** (tested on 3.40.4 and 3.40.6)
- **Python 3.9+** (bundled with QGIS)
- Internet connection for REST service access
- No additional pip packages (uses stdlib + QGIS/Qt only)

---

## Roadmap

- [x] Auto-detect region from loaded layers
- [x] Canvas-center detection (primary) with layer-extent fallback
- [x] OID-paginated REST download engine
- [x] Download safety guardrails
- [x] GeoPackage multi-layer append
- [x] Persistent service bookmarks with layer selections
- [x] SC + NC State Plane CRS detection
- [x] Engineering presets (Drainage Study, Site Assessment, Infrastructure)
- [x] Browse All Layers panel with service directory crawling
- [x] Sketch (light) theme with Medium and Dark options
- [x] Auto pycache cleanup in launcher
- [x] Service health monitoring with color-coded status (Online/Slow/Offline)
- [x] Custom URL tab auto-detects ServiceDirectory URLs and crawls them
- [ ] Download history log for deliverable documentation
- [ ] Settings panel (default CRS, batch size, proxy, SSL)
- [ ] Theme toggle in GUI
- [ ] QGIS Plugin Manager packaging

---

## License

MIT License. See [LICENSE](LICENSE).

---

Built for SE US engineering consulting. Extensible to anywhere with a public ArcGIS REST endpoint.
