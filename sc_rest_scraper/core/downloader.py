"""
downloader.py - ArcGIS REST Feature Download Engine
====================================================
Handles all REST API communication, OID-based pagination,
ESRI JSON to QGIS geometry conversion, and GeoPackage export.

This module is the core workhorse of GeoGrab. It is designed to be
called from the GUI but can also be used standalone from the QGIS
Python Console for scripted workflows.

Usage (standalone):
    from sc_rest_scraper.core.downloader import RESTDownloader
    dl = RESTDownloader()
    layers = dl.get_service_layers(url)
    features, sr = dl.download_features(url, layer_id, bbox=...)
    qgs_layer = dl.to_qgis_layer(features, sr, layer_info)
    dl.save_to_gpkg(qgs_layer, output_path, layer_name)
"""

import json
import math
import ssl
import urllib.request
import urllib.parse
from typing import Optional, Callable

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsField, QgsFields, QgsCoordinateReferenceSystem,
    QgsCoordinateTransform, QgsVectorFileWriter,
    QgsWkbTypes, QgsMessageLog, Qgis
)
from qgis.PyQt.QtCore import QVariant


class RESTDownloader:
    """Stateless download engine for ArcGIS REST services."""

    # Default batch size for OID pagination.
    # Berkeley County has MaxRecordCount=1000, so 500 is safe.
    BATCH_SIZE = 500

    # HTTP request timeout in seconds
    TIMEOUT = 60

    # User agent string for requests
    USER_AGENT = 'GeoGrab-QGIS/1.0'

    def __init__(self, batch_size=None, timeout=None, verify_ssl=False):
        """
        Initialize the downloader.

        Args:
            batch_size: Override default OID batch size
            timeout: Override default HTTP timeout
            verify_ssl: If False (default), skip SSL cert verification.
                        Some county servers have certificate issues.
        """
        if batch_size:
            self.BATCH_SIZE = batch_size
        if timeout:
            self.TIMEOUT = timeout
        self.verify_ssl = verify_ssl

    # -----------------------------------------------------------------
    # HTTP / JSON
    # -----------------------------------------------------------------
    def fetch_json(self, url, params=None):
        """
        Fetch JSON from a URL with optional query parameters.

        Args:
            url: Base URL
            params: Dict of query parameters

        Returns:
            Parsed JSON as dict

        Raises:
            Exception: On network error or non-JSON response
        """
        if params:
            full_url = url + '?' + urllib.parse.urlencode(params)
        else:
            full_url = url

        ctx = ssl.create_default_context()
        if not self.verify_ssl:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(full_url)
        req.add_header('User-Agent', self.USER_AGENT)

        try:
            with urllib.request.urlopen(
                req, timeout=self.TIMEOUT, context=ctx
            ) as resp:
                raw = resp.read().decode('utf-8')
                return json.loads(raw)
        except json.JSONDecodeError as e:
            raise Exception(
                f"Response is not valid JSON from {url}: {e}"
            )
        except Exception as e:
            raise Exception(f"Network error fetching {url}: {e}")

    # -----------------------------------------------------------------
    # Service Discovery
    # -----------------------------------------------------------------
    def get_directory_services(self, directory_url):
        """
        Query a ServiceDirectory URL to list its child services.

        ArcGIS Server service directories return a JSON response with
        a "services" array, each having "name" and "type" fields.
        Child service URLs are constructed as:
            {directory_url}/{service_name}/{service_type}

        Args:
            directory_url: Root URL of the service directory
                (e.g., https://services1.arcgis.com/.../rest/services)

        Returns:
            List of dicts: [{name, url, type, display_name}, ...]
            Only MapServer and FeatureServer entries are returned.
        """
        data = self.fetch_json(directory_url.rstrip('/'), {'f': 'json'})
        results = []
        browsable = {'MapServer', 'FeatureServer'}

        for svc in data.get('services', []):
            svc_name = svc.get('name', '')
            svc_type = svc.get('type', '')
            if svc_type not in browsable:
                continue

            # Build the child service URL
            child_url = f"{directory_url.rstrip('/')}/{svc_name}/{svc_type}"

            # Display name: strip folder prefix if present
            display = svc_name.split('/')[-1] if '/' in svc_name else svc_name

            results.append({
                'name': svc_name,
                'display_name': display,
                'url': child_url,
                'type': svc_type,
            })

        # Sort alphabetically by display name
        results.sort(key=lambda x: x['display_name'].lower())
        return results

    def get_service_layers(self, service_url):
        """
        Query a MapServer/FeatureServer root to list available layers.

        Args:
            service_url: Full URL to the MapServer or FeatureServer

        Returns:
            List of dicts with keys: id, name, type, parent_id
        """
        data = self.fetch_json(service_url.rstrip('/'), {'f': 'json'})
        layers = []
        for lyr in data.get('layers', []):
            layers.append({
                'id': lyr['id'],
                'name': lyr.get('name', f"Layer {lyr['id']}"),
                'type': lyr.get('type', 'Unknown'),
                'parent_id': lyr.get('parentLayerId', -1),
                'sub_layer_ids': lyr.get('subLayerIds', None),
                'min_scale': lyr.get('minScale', 0),
                'max_scale': lyr.get('maxScale', 0),
                'default_visibility': lyr.get('defaultVisibility', True)
            })
        return layers

    def get_layer_info(self, service_url, layer_id):
        """
        Get detailed metadata for a specific layer.

        Returns dict with fields, geometryType, extent, spatialReference, etc.
        """
        url = f"{service_url.rstrip('/')}/{layer_id}"
        return self.fetch_json(url, {'f': 'json'})

    def check_service_health(self, service_url, timeout=10):
        """
        Quick health check on a REST service.

        Returns:
            dict: {alive: bool, response_ms: int, layer_count: int, error: str}
        """
        import time
        start = time.time()
        try:
            old_timeout = self.TIMEOUT
            self.TIMEOUT = timeout
            data = self.fetch_json(service_url.rstrip('/'), {'f': 'json'})
            self.TIMEOUT = old_timeout
            elapsed = int((time.time() - start) * 1000)
            layer_count = len(data.get('layers', []))
            return {
                'alive': True,
                'response_ms': elapsed,
                'layer_count': layer_count,
                'error': None
            }
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return {
                'alive': False,
                'response_ms': elapsed,
                'layer_count': 0,
                'error': str(e)
            }

    # -----------------------------------------------------------------
    # Feature Download
    # -----------------------------------------------------------------
    def download_features(self, service_url, layer_id,
                          geom_filter=None, sr_wkid=None,
                          progress_cb=None):
        """
        Download all features from a REST layer using OID pagination.

        Args:
            service_url: MapServer base URL
            layer_id: Integer layer ID
            geom_filter: Optional dict:
                - {'bbox': 'xmin,ymin,xmax,ymax'} for envelope filter
                - {'rings': [...], 'spatialReference': {'wkid': N}} for polygon
            sr_wkid: Output spatial reference WKID
            progress_cb: Callable(current_pct, total_pct, message)

        Returns:
            Tuple of (features_list, spatial_ref_dict)
        """
        qurl = f"{service_url.rstrip('/')}/{layer_id}/query"

        def _add_geom_params(params):
            """Attach geometry filter to query params."""
            if geom_filter and 'rings' in geom_filter:
                params['geometry'] = json.dumps(geom_filter)
                params['geometryType'] = 'esriGeometryPolygon'
                params['spatialRel'] = 'esriSpatialRelIntersects'
                if sr_wkid:
                    params['inSR'] = str(sr_wkid)
            elif geom_filter and 'bbox' in geom_filter:
                params['geometry'] = geom_filter['bbox']
                params['geometryType'] = 'esriGeometryEnvelope'
                params['spatialRel'] = 'esriSpatialRelIntersects'
                if sr_wkid:
                    params['inSR'] = str(sr_wkid)
            return params

        # Step 1: Count
        if progress_cb:
            progress_cb(0, 100, "Querying feature count...")

        count_params = _add_geom_params({
            'where': '1=1',
            'returnCountOnly': 'true',
            'f': 'json'
        })
        total = self.fetch_json(qurl, count_params).get('count', 0)

        if total == 0:
            if progress_cb:
                progress_cb(100, 100, "No features found in query area.")
            return [], None

        if progress_cb:
            progress_cb(5, 100, f"Found {total} features. Getting OIDs...")

        # Step 2: Get OIDs
        oid_params = _add_geom_params({
            'where': '1=1',
            'returnIdsOnly': 'true',
            'f': 'json'
        })
        oid_resp = self.fetch_json(qurl, oid_params)
        oid_field = oid_resp.get('objectIdFieldName', 'OBJECTID')
        oids = sorted(oid_resp.get('objectIds', []))

        if not oids:
            return [], None

        # Step 3: Batch download
        nb = math.ceil(len(oids) / self.BATCH_SIZE)
        all_feats = []
        sp_ref = None

        for bi in range(nb):
            s = bi * self.BATCH_SIZE
            e = min(s + self.BATCH_SIZE, len(oids))
            batch = oids[s:e]

            if progress_cb:
                pct = int(10 + (bi / nb) * 85)
                progress_cb(
                    pct, 100,
                    f"Batch {bi+1}/{nb}  ({len(all_feats)}/{total})"
                )

            qp = {
                'where': (f"{oid_field}>={batch[0]} "
                          f"AND {oid_field}<={batch[-1]}"),
                'outFields': '*',
                'returnGeometry': 'true',
                'f': 'json'
            }

            # Re-apply geometry filter to each batch
            if geom_filter and 'rings' in geom_filter:
                qp['geometry'] = json.dumps(geom_filter)
                qp['geometryType'] = 'esriGeometryPolygon'
                qp['spatialRel'] = 'esriSpatialRelIntersects'
                if sr_wkid:
                    qp['inSR'] = str(sr_wkid)
            elif geom_filter and 'bbox' in geom_filter:
                qp['geometry'] = geom_filter['bbox']
                qp['geometryType'] = 'esriGeometryEnvelope'
                qp['spatialRel'] = 'esriSpatialRelIntersects'
                if sr_wkid:
                    qp['inSR'] = str(sr_wkid)

            if sr_wkid:
                qp['outSR'] = str(sr_wkid)

            bd = self.fetch_json(qurl, qp)
            all_feats.extend(bd.get('features', []))

            if sp_ref is None and 'spatialReference' in bd:
                sp_ref = bd['spatialReference']

        if progress_cb:
            progress_cb(100, 100, f"Downloaded {len(all_feats)} features.")

        return all_feats, sp_ref

    # -----------------------------------------------------------------
    # ESRI JSON -> QGIS Layer Conversion
    # -----------------------------------------------------------------
    def to_qgis_layer(self, features, spatial_ref, layer_info):
        """
        Convert ESRI JSON features to a QGIS memory layer.

        Args:
            features: List of ESRI JSON feature dicts
            spatial_ref: Spatial reference dict from REST response
            layer_info: Layer metadata dict from get_layer_info()

        Returns:
            QgsVectorLayer (memory provider) or None
        """
        if not features:
            return None

        # Geometry type mapping
        gt_map = {
            'esriGeometryPoint': 'Point',
            'esriGeometryMultipoint': 'MultiPoint',
            'esriGeometryPolyline': 'MultiLineString',
            'esriGeometryPolygon': 'MultiPolygon',
        }
        egt = layer_info.get('geometryType', 'esriGeometryPolygon')
        qgt = gt_map.get(egt, 'MultiPolygon')

        # CRS
        wkid = 4326
        if spatial_ref:
            wkid = spatial_ref.get(
                'latestWkid', spatial_ref.get('wkid', 4326)
            )

        # Field type mapping
        ft_map = {
            'esriFieldTypeOID': QVariant.Int,
            'esriFieldTypeInteger': QVariant.Int,
            'esriFieldTypeSmallInteger': QVariant.Int,
            'esriFieldTypeDouble': QVariant.Double,
            'esriFieldTypeSingle': QVariant.Double,
            'esriFieldTypeString': QVariant.String,
            'esriFieldTypeDate': QVariant.String,
            'esriFieldTypeGlobalID': QVariant.String,
            'esriFieldTypeGUID': QVariant.String,
        }

        # Build fields
        fields = QgsFields()
        fnames = []
        for fd in layer_info.get('fields', []):
            fn = fd['name']
            ft = ft_map.get(fd.get('type', ''), QVariant.String)
            ln = fd.get('length', 0)
            if ft == QVariant.String:
                fields.append(QgsField(fn, ft, 'String', ln or 254))
            elif ft == QVariant.Int:
                fields.append(QgsField(fn, ft, 'Integer'))
            elif ft == QVariant.Double:
                fields.append(QgsField(fn, ft, 'Real'))
            else:
                fields.append(QgsField(fn, QVariant.String, 'String', 254))
            fnames.append(fn)

        # Create memory layer
        lname = layer_info.get('name', 'REST_Download')
        ml = QgsVectorLayer(
            f"{qgt}?crs=EPSG:{wkid}", lname, "memory"
        )
        prov = ml.dataProvider()
        prov.addAttributes(fields)
        ml.updateFields()

        # Convert features
        new_feats = []
        skipped = 0

        for fj in features:
            gj = fj.get('geometry')
            at = fj.get('attributes', {})
            if gj is None:
                skipped += 1
                continue

            feat = QgsFeature(ml.fields())
            try:
                geom = self._convert_geometry(egt, gj)
                if geom and not geom.isNull():
                    feat.setGeometry(geom)
                else:
                    skipped += 1
                    continue
            except Exception:
                skipped += 1
                continue

            # Set attributes
            for fn in fnames:
                v = at.get(fn)
                try:
                    feat.setAttribute(fn, v)
                except Exception:
                    feat.setAttribute(
                        fn, str(v) if v is not None else None
                    )
            new_feats.append(feat)

        prov.addFeatures(new_feats)
        ml.updateExtents()

        if skipped:
            QgsMessageLog.logMessage(
                f"GeoGrab: Skipped {skipped} null/invalid geometries "
                f"from {lname}",
                "GeoGrab", Qgis.Warning
            )

        return ml

    def _convert_geometry(self, esri_type, geom_json):
        """Convert an ESRI JSON geometry to QgsGeometry."""
        if esri_type == 'esriGeometryPolygon':
            rings = geom_json.get('rings', [])
            if not rings:
                return None
            parts = []
            for r in rings:
                coords = ', '.join(f"{p[0]} {p[1]}" for p in r)
                parts.append(f"({coords})")
            g = QgsGeometry.fromWkt(f"POLYGON({', '.join(parts)})")
            if not g.isNull():
                g.convertToMultiType()
            return g

        elif esri_type == 'esriGeometryPolyline':
            paths = geom_json.get('paths', [])
            if not paths:
                return None
            parts = []
            for pa in paths:
                coords = ', '.join(f"{p[0]} {p[1]}" for p in pa)
                parts.append(f"({coords})")
            return QgsGeometry.fromWkt(
                f"MULTILINESTRING({', '.join(parts)})"
            )

        elif esri_type == 'esriGeometryPoint':
            x = geom_json.get('x', 0)
            y = geom_json.get('y', 0)
            return QgsGeometry.fromWkt(f"POINT({x} {y})")

        return None

    # -----------------------------------------------------------------
    # Export
    # -----------------------------------------------------------------
    def save_to_gpkg(self, layer, output_path, layer_name=None):
        """
        Save a QgsVectorLayer to GeoPackage.

        If the .gpkg file already exists, appends a new layer to it
        instead of overwriting the entire file. If the file exists
        AND already contains a layer with the same name, that layer
        is overwritten but other layers are preserved.

        Args:
            layer: QgsVectorLayer to save
            output_path: Full path to .gpkg file
            layer_name: Name for the layer within the GeoPackage

        Returns:
            True on success

        Raises:
            Exception on write error
        """
        import os

        opts = QgsVectorFileWriter.SaveVectorOptions()
        opts.driverName = "GPKG"
        opts.layerName = layer_name or layer.name()

        # If the file already exists, append instead of overwriting
        if os.path.exists(output_path):
            opts.actionOnExistingFile = (
                QgsVectorFileWriter.CreateOrOverwriteLayer
            )

        err, msg, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, output_path,
            QgsProject.instance().transformContext(),
            opts
        )
        if err != QgsVectorFileWriter.NoError:
            raise Exception(f"GeoPackage write error: {msg}")
        return True

    def load_gpkg_to_map(self, gpkg_path, layer_name, display_name=None):
        """
        Load a GeoPackage layer into the current QGIS project.

        Returns:
            QgsVectorLayer if valid, None otherwise
        """
        uri = f"{gpkg_path}|layername={layer_name}"
        lyr = QgsVectorLayer(uri, display_name or layer_name, "ogr")
        if lyr.isValid():
            QgsProject.instance().addMapLayer(lyr)
            return lyr
        return None
