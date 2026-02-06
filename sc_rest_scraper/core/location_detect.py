"""
location_detect.py - Auto-detect project location from QGIS layers
===================================================================
Examines loaded layers to determine which SC county/region the user
is working in, then suggests relevant REST services from the registry.
"""

import json
import os

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsRectangle, QgsPointXY
)


class LocationDetector:
    """Detects project location and matches to SC service registry."""

    # State Plane EPSG codes (strong indicator of SE US work)
    KNOWN_STATE_PLANE_CODES = {
        # SC State Plane
        2273, 3361, 6570, 32133, 32033, 102733,
        # NC State Plane (for NC county support)
        2264, 3358, 6543, 32119, 102719,
    }

    def __init__(self, registry_path=None):
        """
        Args:
            registry_path: Path to sc_services.json.
                           If None, looks relative to this file.
        """
        if registry_path is None:
            config_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 'config'
            )
            registry_path = os.path.join(config_dir, 'sc_services.json')

        self.registry_path = registry_path
        self.registry = None

    def _load_registry(self):
        """Load the service registry JSON."""
        if self.registry is None:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                self.registry = json.load(f)
        return self.registry

    def get_project_extent_wgs84(self):
        """
        Compute the combined bounding box of all loaded layers,
        transformed to WGS84 (EPSG:4326).

        Returns:
            QgsRectangle in WGS84, or None if no layers loaded
        """
        project = QgsProject.instance()
        layers = project.mapLayers().values()

        if not layers:
            return None

        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        combined = QgsRectangle()
        has_extent = False

        for lyr in layers:
            ext = lyr.extent()
            if ext.isNull() or ext.isEmpty():
                continue

            lyr_crs = lyr.crs()
            if lyr_crs != wgs84 and lyr_crs.isValid():
                xform = QgsCoordinateTransform(
                    lyr_crs, wgs84, project
                )
                try:
                    ext = xform.transformBoundingBox(ext)
                except Exception:
                    continue

            if has_extent:
                combined.combineExtentWith(ext)
            else:
                combined = ext
                has_extent = True

        return combined if has_extent else None

    def get_project_crs_info(self):
        """
        Analyze CRS of loaded layers to detect SC State Plane usage.

        Returns:
            dict: {
                is_south_carolina: bool,
                primary_crs: QgsCoordinateReferenceSystem,
                epsg_code: int,
                layer_count: int
            }
        """
        project = QgsProject.instance()
        crs_counts = {}

        for lyr in project.mapLayers().values():
            crs = lyr.crs()
            if crs.isValid():
                auth = crs.authid()
                crs_counts[auth] = crs_counts.get(auth, 0) + 1

        if not crs_counts:
            return {
                'is_south_carolina': False,
                'primary_crs': None,
                'epsg_code': None,
                'layer_count': 0
            }

        # Most common CRS
        primary_auth = max(crs_counts, key=crs_counts.get)
        primary_crs = QgsCoordinateReferenceSystem(primary_auth)

        # Check if it's SC State Plane
        epsg = None
        try:
            epsg = int(primary_auth.split(':')[1])
        except (ValueError, IndexError):
            pass

        is_sc = epsg in self.KNOWN_STATE_PLANE_CODES if epsg else False

        return {
            'is_south_carolina': is_sc,
            'primary_crs': primary_crs,
            'epsg_code': epsg,
            'layer_count': sum(crs_counts.values())
        }

    def detect_region(self):
        """
        Main detection method. Analyzes loaded layers to determine
        which SC county/region the project is in.

        Returns:
            dict: {
                detected: bool,
                region_id: str or None,
                region_name: str or None,
                confidence: 'high'|'medium'|'low',
                all_matches: list of (region_id, region_name, overlap_pct),
                extent_wgs84: QgsRectangle or None,
                crs_info: dict
            }
        """
        reg = self._load_registry()
        extent = self.get_project_extent_wgs84()
        crs_info = self.get_project_crs_info()

        result = {
            'detected': False,
            'region_id': None,
            'region_name': None,
            'confidence': 'low',
            'all_matches': [],
            'extent_wgs84': extent,
            'crs_info': crs_info
        }

        if extent is None:
            return result

        # Check each region's bounding box for overlap
        matches = []
        for region_id, region_data in reg.get('regions', {}).items():
            bbox = region_data.get('bbox_wgs84')
            if not bbox or len(bbox) != 4:
                continue

            reg_rect = QgsRectangle(bbox[0], bbox[1], bbox[2], bbox[3])

            if extent.intersects(reg_rect):
                # Calculate overlap percentage
                intersection = extent.intersect(reg_rect)
                if not intersection.isNull():
                    overlap = (
                        intersection.area() / extent.area() * 100
                        if extent.area() > 0 else 0
                    )
                    matches.append((
                        region_id,
                        region_data['name'],
                        round(overlap, 1)
                    ))

        # Sort by overlap percentage descending
        matches.sort(key=lambda x: x[2], reverse=True)
        result['all_matches'] = matches

        if matches:
            result['detected'] = True
            result['region_id'] = matches[0][0]
            result['region_name'] = matches[0][1]

            # Confidence based on overlap and CRS
            top_overlap = matches[0][2]
            if top_overlap > 80 and crs_info['is_south_carolina']:
                result['confidence'] = 'high'
            elif top_overlap > 50:
                result['confidence'] = 'medium'
            else:
                result['confidence'] = 'low'

        return result

    def get_services_for_region(self, region_id):
        """
        Get all REST services available for a detected region,
        including statewide services.

        Args:
            region_id: Key from regions dict (e.g., 'berkeley_county')

        Returns:
            dict: {
                local: list of service dicts,
                statewide: list of service dicts,
                region_name: str
            }
        """
        reg = self._load_registry()
        region = reg.get('regions', {}).get(region_id, {})

        return {
            'local': region.get('services', []),
            'statewide': reg.get('statewide', []),
            'region_name': region.get('name', region_id),
            'presets': reg.get('engineering_presets', {})
        }

    def detect_region_by_canvas_center(self):
        """
        Alternative detection using the map canvas center point.
        Better for zoomed-in views where layer extents may be much
        larger than the visible area.

        Returns:
            Same dict structure as detect_region().
        """
        from qgis.utils import iface
        reg = self._load_registry()
        crs_info = self.get_project_crs_info()

        canvas = iface.mapCanvas()
        center = canvas.center()
        canvas_crs = canvas.mapSettings().destinationCrs()
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")

        result = {
            'detected': False,
            'region_id': None,
            'region_name': None,
            'confidence': 'low',
            'all_matches': [],
            'extent_wgs84': None,
            'crs_info': crs_info
        }

        # Transform canvas center to WGS84
        try:
            if canvas_crs != wgs84 and canvas_crs.isValid():
                xform = QgsCoordinateTransform(
                    canvas_crs, wgs84, QgsProject.instance()
                )
                center = xform.transform(center)
        except Exception:
            return result

        # Also get canvas extent in WGS84
        try:
            ext = canvas.extent()
            if canvas_crs != wgs84 and canvas_crs.isValid():
                xform = QgsCoordinateTransform(
                    canvas_crs, wgs84, QgsProject.instance()
                )
                ext = xform.transformBoundingBox(ext)
            result['extent_wgs84'] = ext
        except Exception:
            pass

        # Check which region bboxes contain the center point
        matches = []
        for region_id, region_data in reg.get('regions', {}).items():
            bbox = region_data.get('bbox_wgs84')
            if not bbox or len(bbox) != 4:
                continue

            reg_rect = QgsRectangle(bbox[0], bbox[1], bbox[2], bbox[3])
            if reg_rect.contains(QgsPointXY(center)):
                # Score by smallest bbox (most specific)
                area = reg_rect.area()
                matches.append((
                    region_id,
                    region_data['name'],
                    area
                ))

        # Sort by smallest bbox first (most specific match)
        matches.sort(key=lambda x: x[2])

        if matches:
            result['detected'] = True
            result['region_id'] = matches[0][0]
            result['region_name'] = matches[0][1]

            # Canvas-center detection is inherently higher confidence
            if crs_info['is_south_carolina']:
                result['confidence'] = 'high'
            else:
                result['confidence'] = 'medium'

            # Store matches
            result['all_matches'] = [
                (rid, rname, round(100.0 / (1 + area), 1))
                for rid, rname, area in matches
            ]

        return result

    # Service types that can be queried for feature layers directly
    BROWSABLE_TYPES = {'MapServer', 'FeatureServer'}
    # Service types that are directory listings of child services
    DIRECTORY_TYPES = {'ServiceDirectory'}
    # Service types that cannot be browsed via REST
    NON_BROWSABLE_TYPES = {'WebApp', 'Portal', 'OpenDataHub', 'ImageServer'}

    def get_all_service_urls(self, region_id):
        """
        Return a flat list of all unique service URLs for a region,
        including statewide services. Each entry includes a 'svc_type'
        field so the GUI can handle directories vs direct endpoints.

        Only includes MapServer, FeatureServer, and ServiceDirectory.
        Skips WebApp, Portal, OpenDataHub, ImageServer.

        Returns:
            list of dict: [{url, name, is_statewide, svc_type}, ...]
        """
        services = self.get_services_for_region(region_id)
        allowed = self.BROWSABLE_TYPES | self.DIRECTORY_TYPES
        result = []
        seen = set()

        for svc in services['local']:
            url = svc['url']
            svc_type = svc.get('type', 'MapServer')
            if url not in seen and svc_type in allowed:
                seen.add(url)
                result.append({
                    'url': url,
                    'name': svc['name'],
                    'is_statewide': False,
                    'svc_type': svc_type,
                })
        for svc in services['statewide']:
            url = svc.get('url', '')
            svc_type = svc.get('type', 'MapServer')
            if url and url not in seen and svc_type in allowed:
                seen.add(url)
                result.append({
                    'url': url,
                    'name': svc['name'],
                    'is_statewide': True,
                    'svc_type': svc_type,
                })
        return result

    def find_layer_by_type(self, region_id, layer_type):
        """
        Find the best service and layer ID for a given data type
        (e.g., 'parcels', 'flood_zones') in a region.

        Args:
            region_id: Region key
            layer_type: One of: parcels, flood_zones, zoning, roads, etc.

        Returns:
            dict: {service_url, layer_id_hint, layer_name, service_name}
            or None if not found
        """
        services = self.get_services_for_region(region_id)

        # Check local services first
        for svc in services['local']:
            known = svc.get('known_layers', {})
            if layer_type in known:
                lyr_info = known[layer_type]
                return {
                    'service_url': svc['url'],
                    'service_name': svc['name'],
                    'layer_name': lyr_info.get('name', layer_type),
                    'layer_id': lyr_info.get('id'),
                    'layer_id_hint': lyr_info.get('id_hint', ''),
                }

        # Check statewide services
        for svc in services['statewide']:
            known = svc.get('known_layers', {})
            if layer_type in known:
                lyr_info = known[layer_type]
                return {
                    'service_url': svc['url'],
                    'service_name': svc['name'],
                    'layer_name': lyr_info.get('name', layer_type),
                    'layer_id': lyr_info.get('id'),
                    'layer_id_hint': lyr_info.get('id_hint', ''),
                }

        return None
