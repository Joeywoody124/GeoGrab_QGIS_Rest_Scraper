# Contributing to GeoGrab

Thanks for your interest in contributing! GeoGrab is a QGIS tool for downloading ArcGIS REST service data, built primarily for South Carolina municipal/county engineering consulting but designed to be extensible.

## How to Contribute

### Adding a New Region

The fastest way to contribute is adding your county or municipality to the service registry.

1. Open `sc_rest_scraper/config/sc_services.json`
2. Add a new entry under `"regions"` following the existing pattern
3. Required fields:
   - `name`: Display name
   - `fips`: County FIPS code
   - `state`: Two-letter state abbreviation
   - `bbox_wgs84`: Bounding box as `[xmin, ymin, xmax, ymax]` in WGS84
   - `services`: Array of REST service objects
4. For each service, include `known_layers` mapping common layer types (`parcels`, `zoning`, `roads`, `flood_zones`, etc.) to the service's layer names and IDs
5. Test by loading a project in that region and verifying auto-detection works

### Reporting Broken Services

Government REST services go offline or change URLs periodically. If you find a broken service:

1. Open an issue with the service name and URL
2. Include the error message from GeoGrab's log panel
3. If you found the new URL, include that too

### Code Contributions

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Follow PEP 8 style with clear inline comments
4. Test in QGIS 3.40+ before submitting
5. Submit a pull request

### Development Setup

1. Clone the repo to a local path
2. Update the path in `launcher.py` to match your clone location
3. Open QGIS, load a project with SC layers
4. Run the launcher from the Python Console:
   ```python
   exec(open(r'<your-path>/launcher.py', encoding='utf-8').read())
   ```
5. The force-reimport in `launcher.py` means you can edit code and re-run without restarting QGIS

## Architecture Notes

- `core/downloader.py`: Stateless REST engine. No GUI dependencies.
- `core/location_detect.py`: CRS + bbox analysis for region matching.
- `core/safety.py`: Pre-flight download guardrails. Configurable thresholds.
- `gui/main_dialog.py`: All Qt/GUI code lives here.
- `gui/styles.py`: QSS stylesheets (dark theme).
- `config/sc_services.json`: Shared service registry (tracked in git).
- `config/user_services.json`: Per-user bookmarks (template tracked, contents are personal).

## Code Style

- Python: PEP 8, 79-char lines where practical
- Docstrings: Google style
- Comments: Explain "why" not "what"
- No external pip dependencies (stdlib + QGIS/Qt only)
