"""
safety.py - Download Safety Guardrails
=======================================
Pre-flight checks that run BEFORE any feature download begins.
Prevents accidental mass downloads that could hammer government
servers or produce unexpectedly large files.

All thresholds are configurable through the SafetyConfig dataclass.
The GUI calls check_download_safety() and receives a SafetyVerdict
indicating whether to proceed, warn, or block.

Design principle: Never silently download more than the user expects.
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SafetyConfig:
    """Configurable safety thresholds.

    Adjust these for your workflow. Defaults are tuned for
    typical SC county engineering consulting (site-scale work,
    not statewide bulk downloads).
    """
    # Feature count thresholds
    warn_feature_count: int = 10_000
    block_feature_count: int = 100_000

    # Extent area thresholds (square degrees in WGS84)
    # ~0.01 sq deg is roughly a small municipality
    # ~0.25 sq deg is roughly a full county
    # ~1.0 sq deg is multi-county / dangerous territory
    warn_extent_sq_deg: float = 0.25
    block_extent_sq_deg: float = 2.0

    # Estimated bytes per feature (conservative average for polygons
    # with moderate attribute tables, e.g. parcels)
    est_bytes_per_feature: int = 2_000

    # Maximum file size warning threshold (MB)
    warn_file_size_mb: float = 100.0

    # Count query timeout (seconds). If the server can't even
    # return a count in this time, the dataset is probably huge.
    count_timeout: int = 30

    # Layer types known to be very large at broad extents
    high_density_layer_types: list = field(default_factory=lambda: [
        'parcels', 'address_points', 'building_footprints',
        'contours', 'flood_zones'
    ])


@dataclass
class SafetyVerdict:
    """Result of a pre-flight safety check.

    Attributes:
        action: 'proceed', 'warn', or 'block'
        feature_count: Actual count from the server (or -1 if unknown)
        est_file_size_mb: Estimated output file size in MB
        extent_sq_deg: Area of the query extent in square degrees
        messages: List of human-readable warning/block messages
        details: Dict of raw check results for logging
    """
    action: str = 'proceed'
    feature_count: int = 0
    est_file_size_mb: float = 0.0
    extent_sq_deg: float = 0.0
    messages: list = field(default_factory=list)
    details: dict = field(default_factory=dict)

    @property
    def is_safe(self):
        return self.action == 'proceed'

    @property
    def needs_confirmation(self):
        return self.action == 'warn'

    @property
    def is_blocked(self):
        return self.action == 'block'

    def summary(self):
        """Single-line summary for log output."""
        parts = [f"{self.action.upper()}: {self.feature_count:,} features"]
        if self.est_file_size_mb > 0:
            parts.append(f"~{self.est_file_size_mb:.1f} MB est.")
        if self.extent_sq_deg > 0:
            parts.append(f"extent {self.extent_sq_deg:.4f} sq deg")
        return " | ".join(parts)


class SafetyChecker:
    """Pre-flight safety analysis for REST downloads.

    Usage:
        checker = SafetyChecker()
        verdict = checker.check(downloader, service_url, layer_id,
                                geom_filter, sr_wkid, layer_type)
        if verdict.is_blocked:
            show_error(verdict.messages)
        elif verdict.needs_confirmation:
            if user_confirms(verdict.messages):
                proceed_with_download()
        else:
            proceed_with_download()
    """

    def __init__(self, config=None):
        self.config = config or SafetyConfig()

    def check(self, downloader, service_url, layer_id,
              geom_filter=None, sr_wkid=None,
              layer_type=None, extent_rect=None):
        """
        Run all pre-flight safety checks.

        Args:
            downloader: RESTDownloader instance (for count query)
            service_url: MapServer base URL
            layer_id: Integer layer ID
            geom_filter: Geometry filter dict (bbox or rings)
            sr_wkid: Spatial reference WKID
            layer_type: Optional string like 'parcels', 'contours'
                        for density-aware warnings
            extent_rect: Optional (xmin, ymin, xmax, ymax) in WGS84
                         for extent area checks

        Returns:
            SafetyVerdict
        """
        verdict = SafetyVerdict()
        cfg = self.config

        # ----------------------------------------------------------
        # Check 1: Extent area (fast, no network call)
        # ----------------------------------------------------------
        if extent_rect:
            xmin, ymin, xmax, ymax = extent_rect
            width = abs(xmax - xmin)
            height = abs(ymax - ymin)
            area = width * height
            verdict.extent_sq_deg = area
            verdict.details['extent_area_sq_deg'] = area
            verdict.details['extent_width_deg'] = width
            verdict.details['extent_height_deg'] = height

            # Rough miles conversion at SC latitude (~33 deg N)
            # 1 deg lat ~ 69 miles, 1 deg lon ~ 58 miles at 33N
            area_sq_miles = (width * 58) * (height * 69)
            verdict.details['extent_area_sq_miles'] = round(area_sq_miles, 1)

            if area >= cfg.block_extent_sq_deg:
                verdict.action = 'block'
                verdict.messages.append(
                    f"Query extent is extremely large: "
                    f"~{area_sq_miles:,.0f} sq miles "
                    f"({area:.3f} sq degrees). "
                    f"This would likely download hundreds of thousands "
                    f"of features. Zoom in or use a clip layer."
                )
                return verdict

            if area >= cfg.warn_extent_sq_deg:
                verdict.messages.append(
                    f"Large query extent: ~{area_sq_miles:,.0f} sq miles. "
                    f"Consider using a clip layer for targeted results."
                )
                # Don't return yet -- still run count check

        # ----------------------------------------------------------
        # Check 2: No spatial filter at all
        # ----------------------------------------------------------
        if geom_filter is None:
            verdict.action = 'block'
            verdict.messages.append(
                "No spatial filter detected. Downloading an entire "
                "service layer without a bounding box or clip polygon "
                "is not allowed. Use the map canvas extent or select "
                "a clip layer."
            )
            return verdict

        # ----------------------------------------------------------
        # Check 3: Feature count (requires network call)
        # ----------------------------------------------------------
        count = self._get_feature_count(
            downloader, service_url, layer_id,
            geom_filter, sr_wkid
        )
        verdict.feature_count = count
        verdict.details['raw_count'] = count

        if count < 0:
            # Count query failed or timed out
            verdict.messages.append(
                "Could not determine feature count from the server. "
                "The dataset may be very large or the server may be "
                "slow. Proceed with caution."
            )
            if verdict.action != 'block':
                verdict.action = 'warn'
            return verdict

        # Estimate file size
        est_bytes = count * cfg.est_bytes_per_feature
        verdict.est_file_size_mb = est_bytes / (1024 * 1024)

        # Density-aware adjustments for known heavy layer types
        is_dense = (
            layer_type
            and layer_type.lower() in cfg.high_density_layer_types
        )
        effective_warn = cfg.warn_feature_count
        effective_block = cfg.block_feature_count
        if is_dense and verdict.extent_sq_deg > 0.1:
            # Tighter limits for parcels/contours at broad extents
            effective_warn = min(effective_warn, 5_000)
            effective_block = min(effective_block, 50_000)
            verdict.details['density_adjusted'] = True

        # Apply thresholds
        if count >= effective_block:
            verdict.action = 'block'
            verdict.messages.append(
                f"Feature count ({count:,}) exceeds the safety limit "
                f"of {effective_block:,}. This would produce a "
                f"~{verdict.est_file_size_mb:.0f} MB file and could "
                f"take a very long time. Zoom in or add a clip layer."
            )
        elif count >= effective_warn:
            if verdict.action != 'block':
                verdict.action = 'warn'
            verdict.messages.append(
                f"This will download {count:,} features "
                f"(~{verdict.est_file_size_mb:.0f} MB estimated). "
                f"This may take several minutes."
            )
        else:
            # Count is within safe range
            if not verdict.messages:
                verdict.action = 'proceed'

        # If we have warnings from extent but count is OK,
        # keep 'warn' status
        if verdict.messages and verdict.action == 'proceed':
            verdict.action = 'warn'

        return verdict

    def _get_feature_count(self, downloader, service_url, layer_id,
                           geom_filter, sr_wkid):
        """
        Query the server for feature count within the filter area.

        Returns:
            int: Feature count, or -1 if query fails
        """
        import json as json_mod
        import urllib.parse

        qurl = f"{service_url.rstrip('/')}/{layer_id}/query"

        params = {
            'where': '1=1',
            'returnCountOnly': 'true',
            'f': 'json'
        }

        # Attach geometry filter
        if geom_filter and 'rings' in geom_filter:
            params['geometry'] = json_mod.dumps(geom_filter)
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

        try:
            # Use a shorter timeout for the safety count check
            original_timeout = downloader.TIMEOUT
            downloader.TIMEOUT = self.config.count_timeout
            result = downloader.fetch_json_post(qurl, params)
            downloader.TIMEOUT = original_timeout
            return result.get('count', -1)
        except Exception:
            # Restore timeout even on failure
            try:
                downloader.TIMEOUT = original_timeout
            except Exception:
                pass
            return -1

    def format_confirmation_message(self, verdict):
        """
        Build a user-friendly confirmation dialog message
        from a SafetyVerdict.

        Returns:
            str: Formatted message for QMessageBox
        """
        lines = []

        if verdict.feature_count > 0:
            lines.append(
                f"Features to download: {verdict.feature_count:,}"
            )
        if verdict.est_file_size_mb > 1:
            lines.append(
                f"Estimated file size: ~{verdict.est_file_size_mb:.0f} MB"
            )
        sq_miles = verdict.details.get('extent_area_sq_miles')
        if sq_miles and sq_miles > 10:
            lines.append(
                f"Query area: ~{sq_miles:,.0f} square miles"
            )

        lines.append("")  # blank line
        for msg in verdict.messages:
            lines.append(f"  {msg}")

        if verdict.needs_confirmation:
            lines.append("")
            lines.append("Do you want to proceed with this download?")

        return "\n".join(lines)
