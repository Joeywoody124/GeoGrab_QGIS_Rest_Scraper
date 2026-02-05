# Changelog

All notable changes to GeoGrab are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [1.2.0] - 2026-02-05

### Added
- **Town of Bluffton**: 10 services (9 FeatureServers + service directory) with 60+ datasets including zoning, contours, boundaries, flood zones, wetlands, future land use, storm surge, annexations, and PUDs
- **Georgetown County**: EnerGov MapServer (EPSG:3361 native, MaxRecordCount 5000) and 2022 aerial
- **McDowell County NC**: WebGIS MapServer with addresses, contours, roads, parcels, city limits (EPSG:2264)
- **Buncombe County NC**: bcmap_vt MapServer with 65+ layers (property, streets, addresses)
- **Jasper County**: qPublic/Schneider Corp reference (no direct REST)
- **North Charleston**: Portal reference (uses Charleston County services)
- **Statewide services**: SCDNR REST endpoint, SCDHEC (Hub workaround for 403), NC OneMap
- **NC State Plane CRS detection**: EPSG codes 2264, 3358, 6543, 32119, 102719
- **Persistent layer selections**: My Services tab saves checked layers per service in `user_services.json`, restored on next session
- **Save Selections button**: Persist current check states without reconnecting
- **Duplicate URL detection**: Prompts to update existing bookmark instead of creating duplicates

### Fixed
- **EPSG:3361 missing from CRS detection**: NAD83(HARN)/SC State Plane was not in the known codes list, causing LOW confidence for projects using this CRS
- **Duplicate Bluffton registry entry**: Removed second `bluffton` key from sc_services.json
- **GUI too dark**: New COLORS_MEDIUM palette lifts backgrounds ~15-20% brighter. Original dark theme preserved as `DARK_STYLESHEET_ORIG`

### Changed
- `SC_STATE_PLANE_CODES` renamed to `KNOWN_STATE_PLANE_CODES` (reflects SC + NC support)
- Service registry expanded from 5 to 11 regions
- Statewide services expanded from 7 to 11
- `user_services.json` schema updated to v2.0.0 with layer persistence
- Version bumped to 1.2.0

## [1.1.0] - 2026-02-05

### Added
- **Download safety guardrails** (`core/safety.py`)
  - Pre-flight feature count check before every download
  - Configurable warning threshold (default: 10,000 features)
  - Hard block threshold (default: 100,000 features)
  - Extent area validation (warns > 0.25 sq deg, blocks > 2.0 sq deg)
  - Density-aware limits for parcels, contours, and other heavy layers
  - Blocks downloads with no spatial filter (prevents full-service dumps)
  - User confirmation dialog with feature count, estimated file size, and extent area
- **Beaufort County**: 12 services with all 8 Quick Download layer types mapped
- **Save to My Services** functional (Custom URL tab)

### Fixed
- **GeoPackage append**: Multiple layers download to the same `.gpkg` without overwriting
- **Save service crash**: Replaced broken `QMessageBox.question()` with `QInputDialog.getText()`

### Changed
- `_build_geom_filter()` returns WGS84 extent tuple for safety analysis
- `_on_download()` runs `SafetyChecker.check()` per layer before download
- Download summary reports safety-skipped layers separately

## [1.0.0] - 2026-02-05

### Added
- Initial release of GeoGrab
- Three-tab GUI: Quick Download, Custom URL, My Services
- Auto-detection of SC county from loaded layer CRS and extent
- OID-based paginated download engine
- ESRI JSON to QGIS geometry conversion (Point, Polyline, Polygon)
- GeoPackage export with map loading
- Spatial filtering via bounding box or polygon clip layer with buffer
- Pre-configured SC Lowcountry service registry (Berkeley, Charleston, Dorchester, Mt. Pleasant)
- Statewide services: FEMA NFHL, SCDOT, SCGIC, SCDNR, USGS (Gov Units, NHD, 3DEP)
- Engineering presets: Drainage Study, Site Assessment, Infrastructure Inventory
- Professional dark theme with accent colors
- Development launcher with force-reimport support
