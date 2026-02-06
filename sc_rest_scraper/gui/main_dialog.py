"""
main_dialog.py - GeoGrab Main Window (v1.5.0)
===============================================
Professional tabbed interface for REST service data download.

Tab 1: Quick Download - Auto-detects region, one-click common layers
       + "Browse All Layers" panel with service directory crawling.
         ServiceDirectory entries auto-crawl to list child services
         in a secondary dropdown. Direct MapServer/FeatureServer
         entries connect straight to the layer list.
Tab 2: Custom URL    - Paste any REST URL, browse layers
Tab 3: My Services   - Persistent saved services with layer selections

Detection uses canvas-center as primary, with layer-extent fallback.
Non-browsable service types (WebApp, Portal, etc.) are filtered out.

Launched via: from sc_rest_scraper.gui.main_dialog import launch; launch()
"""

import os
import json
from datetime import datetime

from qgis.utils import iface
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsWkbTypes,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform
)
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFileDialog, QMessageBox,
    QProgressBar, QGroupBox, QSpinBox, QCheckBox, QTextEdit,
    QApplication, QSizePolicy, QTabWidget, QWidget,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QFrame,
    QSplitter, QInputDialog, QListWidget, QListWidgetItem
)
from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QFont, QIcon, QColor

from sc_rest_scraper.gui.styles import DARK_STYLESHEET
from sc_rest_scraper.core.downloader import RESTDownloader
from sc_rest_scraper.core.location_detect import LocationDetector
from sc_rest_scraper.core.safety import SafetyChecker, SafetyConfig


class GeoGrabDialog(QDialog):
    """Main GeoGrab application window."""

    VERSION = "1.5.0"

    def __init__(self):
        super().__init__(iface.mainWindow())
        self.setWindowTitle(
            f"GeoGrab  --  REST Data Downloader  v{self.VERSION}"
        )
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowCloseButtonHint
            | Qt.WindowMinMaxButtonsHint
        )
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        # Core objects
        self.downloader = RESTDownloader()
        self.detector = LocationDetector()
        self.safety = SafetyChecker()
        self._detection_result = None
        self._custom_layers = []
        self._svc_layers = []
        self._browse_all_visible = False  # Track browse-all panel state
        self._health_cache = {}  # {url: health_result_dict}

        # Build UI
        self._build()
        self.setStyleSheet(DARK_STYLESHEET)
        self.resize(860, 760)
        self.setMinimumSize(700, 600)

        # Auto-detect on launch
        self._auto_detect()

    # =================================================================
    # BUILD UI
    # =================================================================
    def _build(self):
        L = QVBoxLayout(self)
        L.setSpacing(6)
        L.setContentsMargins(10, 10, 10, 10)

        # -- Header --
        header = QHBoxLayout()
        title = QLabel("GeoGrab")
        title.setStyleSheet(
            "font-size: 18pt; font-weight: bold; color: #2d5da1; "
            "padding: 4px 0;"
        )
        header.addWidget(title)
        subtitle = QLabel("ArcGIS REST Data Downloader for QGIS")
        subtitle.setStyleSheet(
            "font-size: 9pt; color: #6b6b6b; padding-top: 10px;"
        )
        header.addWidget(subtitle)
        header.addStretch()
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet(
            "font-size: 9pt; padding: 4px 10px; border-radius: 3px;"
        )
        header.addWidget(self.lbl_status)
        L.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #c5bfb3;")
        L.addWidget(sep)

        # -- Tabs --
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_quick_tab(), "Quick Download")
        self.tabs.addTab(self._build_custom_tab(), "Custom URL")
        self.tabs.addTab(self._build_services_tab(), "My Services")
        L.addWidget(self.tabs)

        # -- Output section --
        out_group = QGroupBox("Output")
        out_lay = QVBoxLayout(out_group)
        h_out = QHBoxLayout()
        self.txt_output = QLineEdit()
        self.txt_output.setPlaceholderText("Select output .gpkg file...")
        h_out.addWidget(self.txt_output)
        btn_browse = QPushButton("Browse...")
        btn_browse.setFixedWidth(90)
        btn_browse.clicked.connect(self._browse_output)
        h_out.addWidget(btn_browse)
        out_lay.addLayout(h_out)

        h_opts = QHBoxLayout()
        self.chk_add_map = QCheckBox("Add to map")
        self.chk_add_map.setChecked(True)
        h_opts.addWidget(self.chk_add_map)
        h_opts.addStretch()
        self.chk_clip = QCheckBox("Clip to layer:")
        h_opts.addWidget(self.chk_clip)
        self.cbo_clip = QComboBox()
        self.cbo_clip.setMinimumWidth(200)
        self._populate_clip_layers()
        h_opts.addWidget(self.cbo_clip)
        lbl_buf = QLabel("Buffer:")
        h_opts.addWidget(lbl_buf)
        self.spn_buf = QSpinBox()
        self.spn_buf.setRange(0, 50000)
        self.spn_buf.setValue(500)
        self.spn_buf.setSuffix(" ft")
        self.spn_buf.setFixedWidth(100)
        h_opts.addWidget(self.spn_buf)
        out_lay.addLayout(h_opts)
        L.addWidget(out_group)

        # -- Progress --
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFormat("Ready")
        self.progress.setValue(0)
        L.addWidget(self.progress)

        # -- Log --
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(100)
        self.log_box.setPlaceholderText("Download log...")
        L.addWidget(self.log_box)

        # -- Action buttons --
        h_btn = QHBoxLayout()
        h_btn.addStretch()
        self.btn_download = QPushButton("  Download Selected  ")
        self.btn_download.setObjectName("btn_download")
        self.btn_download.setMinimumHeight(38)
        self.btn_download.clicked.connect(self._on_download)
        h_btn.addWidget(self.btn_download)
        btn_close = QPushButton("Close")
        btn_close.setMinimumHeight(38)
        btn_close.setFixedWidth(90)
        btn_close.clicked.connect(self.close)
        h_btn.addWidget(btn_close)
        L.addLayout(h_btn)

    # -----------------------------------------------------------------
    # TAB 1: Quick Download (with Browse All Layers)
    # -----------------------------------------------------------------
    def _build_quick_tab(self):
        w = QWidget()
        L = QVBoxLayout(w)
        L.setSpacing(8)

        # -- Detection row --
        det_row = QHBoxLayout()
        det_row.addWidget(QLabel("Detected Region:"))
        self.lbl_region = QLabel("Detecting...")
        self.lbl_region.setStyleSheet(
            "font-weight: bold; color: #2d5da1; font-size: 10pt;"
        )
        det_row.addWidget(self.lbl_region)
        det_row.addStretch()
        btn_refresh = QPushButton("Re-detect")
        btn_refresh.setFixedWidth(80)
        btn_refresh.clicked.connect(self._auto_detect)
        det_row.addWidget(btn_refresh)
        self.cbo_region_override = QComboBox()
        self.cbo_region_override.setFixedWidth(180)
        self.cbo_region_override.addItem("(auto-detect)")
        self.cbo_region_override.currentIndexChanged.connect(
            self._on_region_changed
        )
        det_row.addWidget(self.cbo_region_override)
        L.addLayout(det_row)

        # -- Quick layers label + Browse All button --
        quick_hdr = QHBoxLayout()
        quick_hdr.addWidget(QLabel("Available Data Layers:"))
        quick_hdr.addStretch()
        self.btn_browse_all = QPushButton("Browse All Layers...")
        self.btn_browse_all.setToolTip(
            "Connect to the detected region's services and list "
            "ALL available layers (like v1). Requires network."
        )
        self.btn_browse_all.clicked.connect(self._toggle_browse_all)
        quick_hdr.addWidget(self.btn_browse_all)
        L.addLayout(quick_hdr)

        # -- Quick layers tree (mapped types) --
        self.tree_quick = QTreeWidget()
        self.tree_quick.setHeaderLabels(["Layer", "Source", "Status"])
        self.tree_quick.setAlternatingRowColors(True)
        self.tree_quick.setRootIsDecorated(False)
        hdr = self.tree_quick.header()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        L.addWidget(self.tree_quick)

        # -- Browse-all panel (hidden by default) --
        self.browse_all_widget = QWidget()
        ba_lay = QVBoxLayout(self.browse_all_widget)
        ba_lay.setContentsMargins(0, 4, 0, 0)
        ba_lay.setSpacing(4)

        ba_hdr = QHBoxLayout()
        ba_hdr.addWidget(QLabel("All Layers from Region Services:"))
        ba_hdr.addStretch()

        # Service selector combo
        self.cbo_browse_service = QComboBox()
        self.cbo_browse_service.setMinimumWidth(280)
        self.cbo_browse_service.setPlaceholderText(
            "Select a service to browse..."
        )
        self.cbo_browse_service.currentIndexChanged.connect(
            self._on_browse_service_changed
        )
        ba_hdr.addWidget(self.cbo_browse_service)

        self.btn_browse_connect = QPushButton("Connect")
        self.btn_browse_connect.setFixedWidth(80)
        self.btn_browse_connect.clicked.connect(self._on_browse_connect)
        ba_hdr.addWidget(self.btn_browse_connect)
        ba_lay.addLayout(ba_hdr)

        # Sub-service selector (shown only for ServiceDirectory entries)
        self.browse_sub_row = QHBoxLayout()
        self.lbl_browse_sub = QLabel("  Child Service:")
        self.browse_sub_row.addWidget(self.lbl_browse_sub)
        self.cbo_browse_sub = QComboBox()
        self.cbo_browse_sub.setMinimumWidth(320)
        self.cbo_browse_sub.setPlaceholderText(
            "Crawling directory... select a child service"
        )
        self.browse_sub_row.addWidget(self.cbo_browse_sub)
        self.browse_sub_row.addStretch()
        ba_lay.addLayout(self.browse_sub_row)
        # Hide sub-service row initially
        self.lbl_browse_sub.setVisible(False)
        self.cbo_browse_sub.setVisible(False)

        self.tree_browse_all = QTreeWidget()
        self.tree_browse_all.setHeaderLabels(
            ["", "ID", "Layer Name", "Type"]
        )
        self.tree_browse_all.setAlternatingRowColors(True)
        self.tree_browse_all.setRootIsDecorated(False)
        bdr = self.tree_browse_all.header()
        bdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        bdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        bdr.setSectionResizeMode(2, QHeaderView.Stretch)
        bdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tree_browse_all.setMaximumHeight(180)
        ba_lay.addWidget(self.tree_browse_all)

        self.browse_all_widget.setVisible(False)
        L.addWidget(self.browse_all_widget)

        # -- Preset row --
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Presets:"))
        for pid, plbl in [('drainage_study', 'Drainage Study'),
                          ('site_assessment', 'Site Assessment'),
                          ('infrastructure_inventory', 'Infrastructure')]:
            b = QPushButton(plbl)
            b.clicked.connect(lambda _, p=pid: self._apply_preset(p))
            preset_row.addWidget(b)
        btn_all = QPushButton("Select All")
        btn_all.clicked.connect(self._select_all_quick)
        preset_row.addWidget(btn_all)
        btn_none = QPushButton("Clear")
        btn_none.clicked.connect(self._clear_all_quick)
        preset_row.addWidget(btn_none)
        preset_row.addStretch()
        L.addLayout(preset_row)
        return w

    # -----------------------------------------------------------------
    # TAB 2: Custom URL
    # -----------------------------------------------------------------
    def _build_custom_tab(self):
        w = QWidget()
        L = QVBoxLayout(w)
        L.setSpacing(8)

        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("REST Service URL:"))
        self.txt_custom_url = QLineEdit()
        self.txt_custom_url.setPlaceholderText(
            "https://example.com/arcgis/rest/services/.../MapServer"
        )
        url_row.addWidget(self.txt_custom_url)
        btn_go = QPushButton("Connect")
        btn_go.setFixedWidth(90)
        btn_go.clicked.connect(self._on_custom_connect)
        url_row.addWidget(btn_go)
        L.addLayout(url_row)

        # Sub-service selector (shown when URL is a ServiceDirectory)
        self.custom_sub_row = QHBoxLayout()
        self.lbl_custom_sub = QLabel("  Child Service:")
        self.custom_sub_row.addWidget(self.lbl_custom_sub)
        self.cbo_custom_sub = QComboBox()
        self.cbo_custom_sub.setMinimumWidth(320)
        self.cbo_custom_sub.setPlaceholderText(
            "Select a child service..."
        )
        self.custom_sub_row.addWidget(self.cbo_custom_sub)
        self.btn_custom_sub_connect = QPushButton("Browse")
        self.btn_custom_sub_connect.setFixedWidth(80)
        self.btn_custom_sub_connect.clicked.connect(
            self._on_custom_sub_connect
        )
        self.custom_sub_row.addWidget(self.btn_custom_sub_connect)
        self.custom_sub_row.addStretch()
        L.addLayout(self.custom_sub_row)
        # Hide sub-service row initially
        self.lbl_custom_sub.setVisible(False)
        self.cbo_custom_sub.setVisible(False)
        self.btn_custom_sub_connect.setVisible(False)

        self.tree_custom = QTreeWidget()
        self.tree_custom.setHeaderLabels(
            ["", "ID", "Layer Name", "Type"]
        )
        self.tree_custom.setAlternatingRowColors(True)
        hdr = self.tree_custom.header()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        L.addWidget(self.tree_custom)

        h_save = QHBoxLayout()
        h_save.addStretch()
        btn_save_svc = QPushButton("Save to My Services")
        btn_save_svc.clicked.connect(self._save_custom_service)
        h_save.addWidget(btn_save_svc)
        L.addLayout(h_save)
        return w

    # -----------------------------------------------------------------
    # TAB 3: My Services
    # -----------------------------------------------------------------
    def _build_services_tab(self):
        w = QWidget()
        L = QVBoxLayout(w)
        L.setSpacing(8)

        L.addWidget(QLabel(
            "Saved services persist between sessions. "
            "Select a service, then check layers to download."
        ))

        splitter = QSplitter(Qt.Horizontal)

        # Left: service list
        left_w = QWidget()
        left_L = QVBoxLayout(left_w)
        left_L.setContentsMargins(0, 0, 4, 0)
        left_L.addWidget(QLabel("Saved Services:"))
        self.list_services = QListWidget()
        self.list_services.setAlternatingRowColors(True)
        self.list_services.currentRowChanged.connect(
            self._on_service_selected
        )
        left_L.addWidget(self.list_services)

        h_svc_btns = QHBoxLayout()
        btn_svc_del = QPushButton("Delete")
        btn_svc_del.setFixedWidth(70)
        btn_svc_del.clicked.connect(self._delete_saved_service)
        h_svc_btns.addWidget(btn_svc_del)
        btn_svc_refresh = QPushButton("Refresh")
        btn_svc_refresh.setFixedWidth(70)
        btn_svc_refresh.clicked.connect(self._on_svc_connect)
        h_svc_btns.addWidget(btn_svc_refresh)
        h_svc_btns.addStretch()
        left_L.addLayout(h_svc_btns)
        splitter.addWidget(left_w)

        # Right: layer tree
        right_w = QWidget()
        right_L = QVBoxLayout(right_w)
        right_L.setContentsMargins(4, 0, 0, 0)

        self.lbl_svc_info = QLabel("Select a service to browse layers")
        self.lbl_svc_info.setStyleSheet(
            "color: #6b6b6b; font-style: italic;"
        )
        right_L.addWidget(self.lbl_svc_info)

        self.tree_svc_layers = QTreeWidget()
        self.tree_svc_layers.setHeaderLabels(
            ["", "ID", "Layer Name", "Type"]
        )
        self.tree_svc_layers.setAlternatingRowColors(True)
        hdr = self.tree_svc_layers.header()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        right_L.addWidget(self.tree_svc_layers)

        h_lyr_btns = QHBoxLayout()
        btn_sel_all = QPushButton("Select All")
        btn_sel_all.setFixedWidth(80)
        btn_sel_all.clicked.connect(self._select_all_svc_layers)
        h_lyr_btns.addWidget(btn_sel_all)
        btn_clr_all = QPushButton("Clear")
        btn_clr_all.setFixedWidth(60)
        btn_clr_all.clicked.connect(self._clear_all_svc_layers)
        h_lyr_btns.addWidget(btn_clr_all)
        h_lyr_btns.addStretch()
        btn_save_sel = QPushButton("Save Selections")
        btn_save_sel.setStyleSheet("color: #d4880f; font-weight: bold;")
        btn_save_sel.clicked.connect(self._save_svc_layer_selections)
        h_lyr_btns.addWidget(btn_save_sel)
        right_L.addLayout(h_lyr_btns)

        splitter.addWidget(right_w)
        splitter.setSizes([240, 500])
        L.addWidget(splitter)

        self._refresh_services_list()
        return w

    # =================================================================
    # HELPERS
    # =================================================================
    def _log(self, msg):
        self.log_box.append(msg)
        QApplication.processEvents()

    def _prog(self, cur, tot, msg):
        self.progress.setValue(cur)
        self.progress.setFormat(msg)
        QApplication.processEvents()

    def _get_user_svc_path(self):
        config_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'config'
        )
        return os.path.join(config_dir, 'user_services.json')

    def _load_user_services(self):
        try:
            with open(self._get_user_svc_path(), 'r',
                       encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {'services': []}

    def _save_user_services(self, data):
        with open(self._get_user_svc_path(), 'w',
                   encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _populate_clip_layers(self):
        self.cbo_clip.clear()
        self.cbo_clip.addItem("(Map Canvas Extent)")
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer):
                if lyr.geometryType() == QgsWkbTypes.PolygonGeometry:
                    self.cbo_clip.addItem(lyr.name(), lyr.id())

    def _browse_output(self):
        p, _ = QFileDialog.getSaveFileName(
            self, "Save GeoPackage",
            os.path.expanduser("~"), "GeoPackage (*.gpkg)"
        )
        if p:
            if not p.lower().endswith('.gpkg'):
                p += '.gpkg'
            self.txt_output.setText(p)

    def _build_geom_filter(self, service_url, layer_id):
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")

        if not self.chk_clip.isChecked():
            c = iface.mapCanvas()
            ext = c.extent()
            ccrs = c.mapSettings().destinationCrs()

            try:
                li = self.downloader.get_layer_info(service_url, layer_id)
                sr = li.get('extent', {}).get('spatialReference', {})
                wk = sr.get('latestWkid', sr.get('wkid', 4326))
            except Exception:
                wk = 4326

            ext_wgs = None
            try:
                if ccrs != wgs84 and ccrs.isValid():
                    xf84 = QgsCoordinateTransform(
                        ccrs, wgs84, QgsProject.instance()
                    )
                    ew = xf84.transformBoundingBox(ext)
                else:
                    ew = ext
                ext_wgs = (
                    ew.xMinimum(), ew.yMinimum(),
                    ew.xMaximum(), ew.yMaximum()
                )
            except Exception:
                pass

            lcrs = QgsCoordinateReferenceSystem(f"EPSG:{wk}")
            if ccrs != lcrs:
                xf = QgsCoordinateTransform(
                    ccrs, lcrs, QgsProject.instance()
                )
                ext = xf.transformBoundingBox(ext)

            bb = (f"{ext.xMinimum()},{ext.yMinimum()},"
                  f"{ext.xMaximum()},{ext.yMaximum()}")
            return {'bbox': bb}, wk, ext_wgs

        lid_str = self.cbo_clip.currentData()
        cl = QgsProject.instance().mapLayer(lid_str)
        if cl is None:
            return None, None, None

        try:
            li = self.downloader.get_layer_info(service_url, layer_id)
            sr = li.get('extent', {}).get('spatialReference', {})
            wk = sr.get('latestWkid', sr.get('wkid', 4326))
        except Exception:
            wk = 4326

        lcrs = QgsCoordinateReferenceSystem(f"EPSG:{wk}")

        from qgis.core import QgsGeometry
        cg = QgsGeometry()
        for ft in cl.getFeatures():
            if cg.isEmpty():
                cg = ft.geometry()
            else:
                cg = cg.combine(ft.geometry())

        if self.spn_buf.value() > 0:
            cg = cg.buffer(self.spn_buf.value(), 16)

        ext_wgs = None
        try:
            cg_copy = QgsGeometry(cg)
            if cl.crs() != wgs84 and cl.crs().isValid():
                xf84 = QgsCoordinateTransform(
                    cl.crs(), wgs84, QgsProject.instance()
                )
                cg_copy.transform(xf84)
            bb84 = cg_copy.boundingBox()
            ext_wgs = (
                bb84.xMinimum(), bb84.yMinimum(),
                bb84.xMaximum(), bb84.yMaximum()
            )
        except Exception:
            pass

        if cl.crs() != lcrs:
            xf = QgsCoordinateTransform(
                cl.crs(), lcrs, QgsProject.instance()
            )
            cg.transform(xf)

        if cg.isMultipart():
            rings = []
            for poly in cg.asMultiPolygon():
                for ring in poly:
                    rings.append([[pt.x(), pt.y()] for pt in ring])
        else:
            rings = []
            for ring in cg.asPolygon():
                rings.append([[pt.x(), pt.y()] for pt in ring])

        return (
            {'rings': rings, 'spatialReference': {'wkid': wk}},
            wk,
            ext_wgs
        )

    # =================================================================
    # AUTO-DETECT (canvas-center primary, layer-extent fallback)
    # =================================================================
    def _auto_detect(self):
        try:
            # Try canvas-center first (better when zoomed in)
            result = self.detector.detect_region_by_canvas_center()

            # Fallback to layer-extent if canvas-center found nothing
            if not result['detected']:
                result = self.detector.detect_region()

            self._detection_result = result

            # Populate region override combo
            reg = self.detector._load_registry()
            self.cbo_region_override.blockSignals(True)
            self.cbo_region_override.clear()
            self.cbo_region_override.addItem("(auto-detect)")
            for rid, rdata in reg.get('regions', {}).items():
                self.cbo_region_override.addItem(rdata['name'], rid)
            self.cbo_region_override.blockSignals(False)

            if result['detected']:
                conf = result['confidence']
                name = result['region_name']
                self.lbl_region.setText(name)
                color_map = {
                    'high': '#3a8a3e', 'medium': '#d4880f',
                    'low': '#d63b3b'
                }
                self.lbl_status.setText(f"  {conf.upper()} confidence  ")
                self.lbl_status.setStyleSheet(
                    f"background-color: {color_map.get(conf, '#666')}; "
                    f"color: #ffffff; font-weight: bold; "
                    f"border-radius: 3px; padding: 4px 10px;"
                )
                self._populate_quick_layers(result['region_id'])
                self._populate_browse_services(result['region_id'])
            else:
                self.lbl_region.setText(
                    "No layers loaded or outside coverage"
                )
                self.lbl_status.setText("  NOT DETECTED  ")
                self.lbl_status.setStyleSheet(
                    "background-color: #c5bfb3; color: #2d2d2d; "
                    "border-radius: 3px; padding: 4px 10px;"
                )
        except Exception as ex:
            self.lbl_region.setText(f"Detection error: {ex}")

    def _on_region_changed(self, idx):
        if idx <= 0:
            self._auto_detect()
            return
        rid = self.cbo_region_override.currentData()
        if rid:
            reg = self.detector._load_registry()
            rdata = reg.get('regions', {}).get(rid, {})
            self.lbl_region.setText(rdata.get('name', rid))
            self.lbl_status.setText("  MANUAL  ")
            self.lbl_status.setStyleSheet(
                "background-color: #2d5da1; color: #ffffff; "
                "font-weight: bold; border-radius: 3px; padding: 4px 10px;"
            )
            self._populate_quick_layers(rid)
            self._populate_browse_services(rid)

    def _populate_quick_layers(self, region_id):
        self.tree_quick.clear()
        layer_types = [
            ('parcels', 'Parcels'),
            ('flood_zones', 'Flood Zones (FEMA NFHL)'),
            ('zoning', 'Zoning'),
            ('roads', 'Roads / Street Centerlines'),
            ('contours', 'Contours'),
            ('address_points', 'Address Points'),
            ('municipal_boundaries', 'Municipal Boundaries'),
            ('building_footprints', 'Building Footprints'),
        ]

        # Collect unique service URLs for health checks
        matches = {}
        for ltype, display_name in layer_types:
            match = self.detector.find_layer_by_type(region_id, ltype)
            matches[ltype] = match
            if match:
                url = match['service_url']
                if url not in self._health_cache:
                    self._health_cache[url] = None  # Mark for checking

        # Run health checks for unchecked services
        urls_to_check = [
            u for u, v in self._health_cache.items() if v is None
        ]
        if urls_to_check:
            self.progress.setFormat("Checking service health...")
            self.progress.setValue(0)
            QApplication.processEvents()
            for i, url in enumerate(urls_to_check):
                pct = int((i / len(urls_to_check)) * 50)
                self.progress.setValue(pct)
                QApplication.processEvents()
                self._health_cache[url] = (
                    self.downloader.check_service_health(url, timeout=5)
                )
            self.progress.setFormat("Ready")
            self.progress.setValue(0)

        for ltype, display_name in layer_types:
            match = matches[ltype]
            item = QTreeWidgetItem()
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Unchecked)
            item.setText(0, display_name)

            if match:
                item.setText(1, match['service_name'])
                item.setData(0, Qt.UserRole, {
                    'layer_type': ltype,
                    'service_url': match['service_url'],
                    'layer_id': match.get('layer_id'),
                    'layer_id_hint': match.get('layer_id_hint', ''),
                    'layer_name': match['layer_name'],
                })

                # Color-code status from health check
                health = self._health_cache.get(match['service_url'])
                if health and health['alive']:
                    ms = health['response_ms']
                    if ms > 2000:
                        item.setText(2, f"Slow ({ms}ms)")
                        item.setForeground(2, QColor('#d4880f'))
                    else:
                        item.setText(2, f"Online ({ms}ms)")
                        item.setForeground(2, QColor('#3a8a3e'))
                elif health and not health['alive']:
                    item.setText(2, "Offline")
                    item.setForeground(2, QColor('#d63b3b'))
                else:
                    item.setText(2, "Available")
                    item.setForeground(2, QColor('#3a8a3e'))
            else:
                item.setText(1, "--")
                item.setText(2, "Not configured")
                item.setForeground(2, QColor('#6b6b6b'))
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)

            self.tree_quick.addTopLevelItem(item)

    def _populate_browse_services(self, region_id):
        """Populate the Browse All service selector with region services."""
        self.cbo_browse_service.blockSignals(True)
        self.cbo_browse_service.clear()
        self.cbo_browse_sub.clear()
        self.lbl_browse_sub.setVisible(False)
        self.cbo_browse_sub.setVisible(False)
        try:
            service_list = self.detector.get_all_service_urls(region_id)
            for svc in service_list:
                prefix = "[State] " if svc['is_statewide'] else ""
                svc_type = svc.get('svc_type', 'MapServer')
                if svc_type == 'ServiceDirectory':
                    prefix += "[Directory] "
                label = f"{prefix}{svc['name']}"
                # Store both url and type as item data
                self.cbo_browse_service.addItem(
                    label,
                    {'url': svc['url'], 'svc_type': svc_type}
                )
        except Exception:
            pass
        self.cbo_browse_service.blockSignals(False)

    # =================================================================
    # BROWSE ALL LAYERS (v1-style discovery on Quick tab)
    # =================================================================
    def _toggle_browse_all(self):
        """Show/hide the browse-all panel."""
        self._browse_all_visible = not self._browse_all_visible
        self.browse_all_widget.setVisible(self._browse_all_visible)
        if self._browse_all_visible:
            self.btn_browse_all.setText("Hide All Layers")
        else:
            self.btn_browse_all.setText("Browse All Layers...")

    def _on_browse_service_changed(self, idx):
        """
        When user changes the service dropdown, detect if it's a
        ServiceDirectory and auto-crawl to populate the sub-service
        combo. For direct MapServer/FeatureServer, hide the sub-combo.
        """
        self.cbo_browse_sub.clear()
        self.tree_browse_all.clear()

        if idx < 0:
            self.lbl_browse_sub.setVisible(False)
            self.cbo_browse_sub.setVisible(False)
            return

        data = self.cbo_browse_service.currentData()
        if not data:
            self.lbl_browse_sub.setVisible(False)
            self.cbo_browse_sub.setVisible(False)
            return

        svc_type = data.get('svc_type', 'MapServer')

        if svc_type == 'ServiceDirectory':
            # Show the sub-service combo and auto-crawl
            self.lbl_browse_sub.setVisible(True)
            self.cbo_browse_sub.setVisible(True)
            self._crawl_directory(data['url'])
        else:
            # Direct service: hide sub-combo
            self.lbl_browse_sub.setVisible(False)
            self.cbo_browse_sub.setVisible(False)

    def _crawl_directory(self, directory_url):
        """
        Crawl a ServiceDirectory and populate the sub-service combo
        with all child MapServer/FeatureServer entries.
        """
        svc_name = self.cbo_browse_service.currentText()
        self._log(f"Crawling directory: {svc_name}")
        self._log(f"  URL: {directory_url}")
        self.progress.setFormat("Crawling directory...")
        self.progress.setValue(10)
        QApplication.processEvents()

        try:
            children = self.downloader.get_directory_services(directory_url)
            self.cbo_browse_sub.clear()

            for child in children:
                label = f"{child['display_name']}  ({child['type']})"
                self.cbo_browse_sub.addItem(label, child['url'])

            n = len(children)
            self._log(
                f"  Found {n} browsable services in {svc_name}"
            )
            self.progress.setFormat(
                f"Directory: {n} services found. Select one and Connect."
            )
            self.progress.setValue(100)

            if n == 0:
                self._log(
                    "  No MapServer/FeatureServer children found. "
                    "This directory may require authentication or "
                    "contain only non-browsable service types."
                )

        except Exception as ex:
            self._log(f"  ERROR crawling directory: {ex}")
            self.progress.setFormat("Directory crawl failed")
            QMessageBox.warning(
                self, "Directory Error",
                f"Could not crawl the service directory:\n\n{ex}"
            )

    def _on_browse_connect(self):
        """
        Connect to the selected service and list ALL feature layers.
        For ServiceDirectory entries, reads from the sub-service combo.
        For direct MapServer/FeatureServer, reads the main combo.
        """
        data = self.cbo_browse_service.currentData()
        if not data:
            QMessageBox.warning(
                self, "No Service",
                "Select a service from the dropdown first."
            )
            return

        svc_type = data.get('svc_type', 'MapServer')

        if svc_type == 'ServiceDirectory':
            # Use the sub-service combo for the actual URL
            url = self.cbo_browse_sub.currentData()
            if not url:
                QMessageBox.warning(
                    self, "No Child Service",
                    "Select a child service from the dropdown first.\n\n"
                    "If the dropdown is empty, the directory may not "
                    "contain any browsable services."
                )
                return
            svc_name = self.cbo_browse_sub.currentText()
        else:
            url = data['url']
            svc_name = self.cbo_browse_service.currentText()

        self._log(f"Browsing all layers: {svc_name}")
        self._log(f"  URL: {url}")
        self.progress.setFormat("Connecting...")
        self.progress.setValue(10)
        QApplication.processEvents()

        try:
            layers = self.downloader.get_service_layers(url)
            self.tree_browse_all.clear()

            count = 0
            for lyr in layers:
                if lyr['type'] != 'Feature Layer':
                    continue
                item = QTreeWidgetItem()
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Unchecked)
                item.setText(1, str(lyr['id']))
                item.setText(2, lyr['name'])
                item.setText(3, lyr['type'])
                item.setData(0, Qt.UserRole, {
                    'service_url': url,
                    'layer_id': lyr['id'],
                    'layer_name': lyr['name'],
                })
                self.tree_browse_all.addTopLevelItem(item)
                count += 1

            self._log(f"  Found {count} feature layers in {svc_name}")
            self.progress.setFormat(
                f"Browse: {count} layers from {svc_name}"
            )
            self.progress.setValue(100)

        except Exception as ex:
            self._log(f"  ERROR browsing: {ex}")
            self.progress.setFormat("Browse failed")
            QMessageBox.warning(self, "Connection Error", str(ex))

    # =================================================================
    # PRESETS
    # =================================================================
    def _apply_preset(self, preset_id):
        reg = self.detector._load_registry()
        preset = reg.get('engineering_presets', {}).get(preset_id, {})
        desired = preset.get('layers', [])
        for i in range(self.tree_quick.topLevelItemCount()):
            item = self.tree_quick.topLevelItem(i)
            data = item.data(0, Qt.UserRole)
            if data and data.get('layer_type') in desired:
                item.setCheckState(0, Qt.Checked)
            else:
                item.setCheckState(0, Qt.Unchecked)

    def _select_all_quick(self):
        for i in range(self.tree_quick.topLevelItemCount()):
            item = self.tree_quick.topLevelItem(i)
            if item.flags() & Qt.ItemIsEnabled:
                item.setCheckState(0, Qt.Checked)

    def _clear_all_quick(self):
        for i in range(self.tree_quick.topLevelItemCount()):
            self.tree_quick.topLevelItem(i).setCheckState(0, Qt.Unchecked)

    # =================================================================
    # CUSTOM URL TAB
    # =================================================================
    def _on_custom_connect(self):
        url = self.txt_custom_url.text().strip().rstrip('/')
        if not url:
            QMessageBox.warning(self, "Missing URL", "Enter a REST URL.")
            return

        self._log(f"Connecting to {url}...")
        self.progress.setFormat("Detecting URL type...")
        self.progress.setValue(5)
        QApplication.processEvents()

        # Reset sub-service row and layer tree
        self.lbl_custom_sub.setVisible(False)
        self.cbo_custom_sub.setVisible(False)
        self.btn_custom_sub_connect.setVisible(False)
        self.cbo_custom_sub.clear()
        self.tree_custom.clear()

        try:
            url_type = self.downloader.detect_url_type(url)

            if url_type == 'directory':
                # It's a ServiceDirectory: crawl and show sub-combo
                self._log(f"  Detected ServiceDirectory. Crawling...")
                self.progress.setFormat("Crawling directory...")
                self.progress.setValue(10)
                QApplication.processEvents()

                children = self.downloader.get_directory_services(url)
                self.cbo_custom_sub.clear()
                for child in children:
                    label = (
                        f"{child['display_name']}  ({child['type']})"
                    )
                    self.cbo_custom_sub.addItem(label, child['url'])

                n = len(children)
                self._log(
                    f"  Found {n} browsable child services. "
                    f"Select one and click Browse."
                )
                self.progress.setFormat(
                    f"Directory: {n} services. Select one and Browse."
                )
                self.progress.setValue(100)

                # Show the sub-service row
                self.lbl_custom_sub.setVisible(True)
                self.cbo_custom_sub.setVisible(True)
                self.btn_custom_sub_connect.setVisible(True)

                if n == 0:
                    self._log(
                        "  No MapServer/FeatureServer children found. "
                        "This directory may require authentication."
                    )
                return

            # Normal MapServer/FeatureServer
            self.progress.setFormat("Fetching layers...")
            self.progress.setValue(30)
            QApplication.processEvents()

            layers = self.downloader.get_service_layers(url)
            self._custom_layers = layers

            for lyr in layers:
                if lyr['type'] != 'Feature Layer':
                    continue
                item = QTreeWidgetItem()
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Unchecked)
                item.setText(1, str(lyr['id']))
                item.setText(2, lyr['name'])
                item.setText(3, lyr['type'])
                item.setData(0, Qt.UserRole, {
                    'service_url': url,
                    'layer_id': lyr['id'],
                    'layer_name': lyr['name'],
                })
                self.tree_custom.addTopLevelItem(item)

            n = self.tree_custom.topLevelItemCount()
            self._log(f"Found {n} feature layers.")
            self.progress.setFormat(f"Connected: {n} layers")
            self.progress.setValue(100)
        except Exception as ex:
            self._log(f"ERROR: {ex}")
            self.progress.setFormat("Connection failed")
            QMessageBox.warning(self, "Connection Error", str(ex))

    def _on_custom_sub_connect(self):
        """Browse layers from a child service selected in the sub-combo."""
        child_url = self.cbo_custom_sub.currentData()
        if not child_url:
            QMessageBox.warning(
                self, "No Service",
                "Select a child service from the dropdown first."
            )
            return

        child_name = self.cbo_custom_sub.currentText()
        self._log(f"Browsing child service: {child_name}")
        self._log(f"  URL: {child_url}")
        self.progress.setFormat("Connecting to child service...")
        self.progress.setValue(10)
        QApplication.processEvents()

        try:
            layers = self.downloader.get_service_layers(child_url)
            self._custom_layers = layers
            self.tree_custom.clear()

            for lyr in layers:
                if lyr['type'] != 'Feature Layer':
                    continue
                item = QTreeWidgetItem()
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Unchecked)
                item.setText(1, str(lyr['id']))
                item.setText(2, lyr['name'])
                item.setText(3, lyr['type'])
                item.setData(0, Qt.UserRole, {
                    'service_url': child_url,
                    'layer_id': lyr['id'],
                    'layer_name': lyr['name'],
                })
                self.tree_custom.addTopLevelItem(item)

            n = self.tree_custom.topLevelItemCount()
            self._log(f"  Found {n} feature layers in {child_name}")
            self.progress.setFormat(f"Connected: {n} layers")
            self.progress.setValue(100)
        except Exception as ex:
            self._log(f"  ERROR: {ex}")
            self.progress.setFormat("Connection failed")
            QMessageBox.warning(self, "Connection Error", str(ex))

    def _save_custom_service(self):
        url = self.txt_custom_url.text().strip()
        if not url:
            QMessageBox.warning(
                self, "No URL", "Connect to a REST service first."
            )
            return

        checked_layers = []
        for i in range(self.tree_custom.topLevelItemCount()):
            item = self.tree_custom.topLevelItem(i)
            data = item.data(0, Qt.UserRole)
            if data:
                checked_layers.append({
                    'id': data['layer_id'],
                    'name': data['layer_name'],
                    'checked': item.checkState(0) == Qt.Checked
                })

        name, ok = QInputDialog.getText(
            self, "Save Service",
            "Enter a name for this service:",
            text=url.split('/services/')[-1].replace('/', ' ').strip()
                 or "My Service"
        )
        if not ok or not name.strip():
            return
        name = name.strip()

        user_data = self._load_user_services()

        for svc in user_data['services']:
            if svc['url'] == url:
                reply = QMessageBox.question(
                    self, "Update Existing?",
                    f"'{svc['name']}' already saved. Update it?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    svc['name'] = name
                    svc['layers'] = checked_layers
                    svc['updated'] = datetime.now().isoformat()
                    self._save_user_services(user_data)
                    self._log(f"Updated service: {name}")
                    self._refresh_services_list()
                return

        user_data['services'].append({
            'name': name,
            'url': url,
            'layers': checked_layers,
            'added': datetime.now().isoformat(),
            'updated': datetime.now().isoformat()
        })
        self._save_user_services(user_data)

        n_chk = sum(1 for l in checked_layers if l['checked'])
        self._log(f"Saved: {name} ({n_chk} layers selected)")
        QMessageBox.information(
            self, "Saved",
            f"'{name}' saved with {n_chk} selected "
            f"/ {len(checked_layers)} total layers."
        )
        self._refresh_services_list()

    # =================================================================
    # MY SERVICES TAB
    # =================================================================
    def _refresh_services_list(self):
        self.list_services.clear()
        user_data = self._load_user_services()
        for idx, svc in enumerate(user_data.get('services', [])):
            n_chk = sum(
                1 for l in svc.get('layers', []) if l.get('checked')
            )
            n_tot = len(svc.get('layers', []))
            label = svc['name']
            if n_tot > 0:
                label += f"  ({n_chk}/{n_tot} layers)"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, idx)
            self.list_services.addItem(item)

    def _on_service_selected(self, row):
        if row < 0:
            return
        user_data = self._load_user_services()
        services = user_data.get('services', [])
        idx = self.list_services.item(row).data(Qt.UserRole)
        if idx is None or idx >= len(services):
            return
        svc = services[idx]

        self.lbl_svc_info.setText(f"{svc['name']}  |  {svc['url']}")
        self.lbl_svc_info.setStyleSheet(
            "color: #2d5da1; font-style: normal; font-weight: bold;"
        )

        self.tree_svc_layers.clear()
        saved_layers = svc.get('layers', [])

        if not saved_layers:
            item = QTreeWidgetItem()
            item.setText(
                2, "(No layers cached. Click Refresh to connect.)"
            )
            item.setForeground(2, QColor('#6b6b6b'))
            self.tree_svc_layers.addTopLevelItem(item)
            return

        for lyr in saved_layers:
            item = QTreeWidgetItem()
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(
                0, Qt.Checked if lyr.get('checked') else Qt.Unchecked
            )
            item.setText(1, str(lyr['id']))
            item.setText(2, lyr['name'])
            item.setText(3, "Feature Layer")
            item.setData(0, Qt.UserRole, {
                'service_url': svc['url'],
                'layer_id': lyr['id'],
                'layer_name': lyr['name'],
            })
            self.tree_svc_layers.addTopLevelItem(item)

    def _on_svc_connect(self):
        row = self.list_services.currentRow()
        if row < 0:
            QMessageBox.warning(
                self, "No Selection", "Select a service first."
            )
            return
        user_data = self._load_user_services()
        services = user_data.get('services', [])
        idx = self.list_services.item(row).data(Qt.UserRole)
        if idx is None or idx >= len(services):
            return
        svc = services[idx]
        url = svc['url']

        self._log(f"Refreshing layers for {svc['name']}...")
        self.progress.setFormat("Connecting...")
        QApplication.processEvents()

        try:
            layers = self.downloader.get_service_layers(url)
            prev_checked = {
                l['id'] for l in svc.get('layers', [])
                if l.get('checked')
            }

            new_layers = []
            self.tree_svc_layers.clear()

            for lyr in layers:
                if lyr['type'] != 'Feature Layer':
                    continue
                is_chk = lyr['id'] in prev_checked
                new_layers.append({
                    'id': lyr['id'],
                    'name': lyr['name'],
                    'checked': is_chk
                })
                item = QTreeWidgetItem()
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(
                    0, Qt.Checked if is_chk else Qt.Unchecked
                )
                item.setText(1, str(lyr['id']))
                item.setText(2, lyr['name'])
                item.setText(3, lyr['type'])
                item.setData(0, Qt.UserRole, {
                    'service_url': url,
                    'layer_id': lyr['id'],
                    'layer_name': lyr['name'],
                })
                self.tree_svc_layers.addTopLevelItem(item)

            svc['layers'] = new_layers
            svc['updated'] = datetime.now().isoformat()
            self._save_user_services(user_data)

            n = self.tree_svc_layers.topLevelItemCount()
            self._log(f"Refreshed: {n} layers from {svc['name']}")
            self.progress.setFormat(f"Refreshed: {n} layers")
            self.progress.setValue(100)
        except Exception as ex:
            self._log(f"ERROR refreshing: {ex}")
            self.progress.setFormat("Refresh failed")
            QMessageBox.warning(self, "Connection Error", str(ex))

    def _save_svc_layer_selections(self):
        row = self.list_services.currentRow()
        if row < 0:
            return
        user_data = self._load_user_services()
        services = user_data.get('services', [])
        idx = self.list_services.item(row).data(Qt.UserRole)
        if idx is None or idx >= len(services):
            return

        updated = []
        for i in range(self.tree_svc_layers.topLevelItemCount()):
            item = self.tree_svc_layers.topLevelItem(i)
            data = item.data(0, Qt.UserRole)
            if data:
                updated.append({
                    'id': data['layer_id'],
                    'name': data['layer_name'],
                    'checked': item.checkState(0) == Qt.Checked
                })

        if updated:
            services[idx]['layers'] = updated
            services[idx]['updated'] = datetime.now().isoformat()
            self._save_user_services(user_data)
            n_chk = sum(1 for l in updated if l['checked'])
            self._log(
                f"Saved: {n_chk} layers selected for "
                f"{services[idx]['name']}"
            )
            self._refresh_services_list()

    def _delete_saved_service(self):
        row = self.list_services.currentRow()
        if row < 0:
            return
        user_data = self._load_user_services()
        services = user_data.get('services', [])
        idx = self.list_services.item(row).data(Qt.UserRole)
        if idx is None or idx >= len(services):
            return
        svc = services[idx]

        reply = QMessageBox.question(
            self, "Delete Service?",
            f"Delete '{svc['name']}' and saved selections?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            services.pop(idx)
            self._save_user_services(user_data)
            self.tree_svc_layers.clear()
            self.lbl_svc_info.setText("Select a service to browse layers")
            self.lbl_svc_info.setStyleSheet(
                "color: #6b6b6b; font-style: italic;"
            )
            self._refresh_services_list()
            self._log(f"Deleted: {svc['name']}")

    def _select_all_svc_layers(self):
        for i in range(self.tree_svc_layers.topLevelItemCount()):
            item = self.tree_svc_layers.topLevelItem(i)
            if item.flags() & Qt.ItemIsEnabled:
                item.setCheckState(0, Qt.Checked)

    def _clear_all_svc_layers(self):
        for i in range(self.tree_svc_layers.topLevelItemCount()):
            self.tree_svc_layers.topLevelItem(i).setCheckState(
                0, Qt.Unchecked
            )

    # =================================================================
    # DOWNLOAD (supports all 3 tabs + browse-all)
    # =================================================================
    def _on_download(self):
        output = self.txt_output.text().strip()
        if not output:
            QMessageBox.warning(self, "Missing", "Select an output path.")
            return

        items_to_download = []
        active_tab = self.tabs.currentIndex()

        if active_tab == 0:
            # Collect from Quick tree
            for i in range(self.tree_quick.topLevelItemCount()):
                item = self.tree_quick.topLevelItem(i)
                if item.checkState(0) == Qt.Checked:
                    data = item.data(0, Qt.UserRole)
                    if data:
                        items_to_download.append(data)
            # Also collect from Browse All tree if visible
            if self._browse_all_visible:
                for i in range(self.tree_browse_all.topLevelItemCount()):
                    item = self.tree_browse_all.topLevelItem(i)
                    if item.checkState(0) == Qt.Checked:
                        data = item.data(0, Qt.UserRole)
                        if data:
                            items_to_download.append(data)
        elif active_tab == 1:
            for i in range(self.tree_custom.topLevelItemCount()):
                item = self.tree_custom.topLevelItem(i)
                if item.checkState(0) == Qt.Checked:
                    data = item.data(0, Qt.UserRole)
                    if data:
                        items_to_download.append(data)
        elif active_tab == 2:
            for i in range(self.tree_svc_layers.topLevelItemCount()):
                item = self.tree_svc_layers.topLevelItem(i)
                if item.checkState(0) == Qt.Checked:
                    data = item.data(0, Qt.UserRole)
                    if data:
                        items_to_download.append(data)

        if not items_to_download:
            QMessageBox.warning(
                self, "Nothing Selected",
                "Check at least one layer to download."
            )
            return

        self.btn_download.setEnabled(False)
        self._log("=" * 50)
        self._log(
            f"Starting download of {len(items_to_download)} layer(s)..."
        )

        success_count = 0
        skipped_by_safety = 0

        for idx, dl_info in enumerate(items_to_download):
            svc_url = dl_info['service_url']
            layer_name = dl_info['layer_name']
            layer_id = dl_info.get('layer_id')
            layer_type = dl_info.get('layer_type')

            self._log(
                f"\n[{idx+1}/{len(items_to_download)}] {layer_name}"
            )

            try:
                if layer_id is None:
                    hint = dl_info.get('layer_id_hint', '')
                    self._log(
                        f"  Searching for layer matching '{hint}'..."
                    )
                    QApplication.processEvents()
                    layers = self.downloader.get_service_layers(svc_url)
                    for lyr in layers:
                        if lyr['type'] == 'Feature Layer':
                            if hint and hint.lower() in lyr['name'].lower():
                                layer_id = lyr['id']
                                self._log(
                                    f"  Found: [{layer_id}] {lyr['name']}"
                                )
                                break
                    if layer_id is None:
                        self._log(
                            "  WARNING: Could not find layer. Skipping."
                        )
                        continue

                linfo = self.downloader.get_layer_info(svc_url, layer_id)
                gf, wk, ext_wgs = self._build_geom_filter(
                    svc_url, layer_id
                )

                self._log("  Running safety pre-check...")
                QApplication.processEvents()

                verdict = self.safety.check(
                    downloader=self.downloader,
                    service_url=svc_url,
                    layer_id=layer_id,
                    geom_filter=gf,
                    sr_wkid=wk,
                    layer_type=layer_type,
                    extent_rect=ext_wgs
                )
                self._log(f"  Safety: {verdict.summary()}")

                if verdict.is_blocked:
                    msg = self.safety.format_confirmation_message(verdict)
                    QMessageBox.warning(
                        self, f"Download Blocked: {layer_name}", msg
                    )
                    self._log("  BLOCKED by safety check. Skipping.")
                    skipped_by_safety += 1
                    continue

                if verdict.needs_confirmation:
                    msg = self.safety.format_confirmation_message(verdict)
                    reply = QMessageBox.question(
                        self, f"Large Download: {layer_name}", msg,
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                    )
                    if reply != QMessageBox.Yes:
                        self._log("  User declined. Skipping.")
                        skipped_by_safety += 1
                        continue
                    self._log("  User confirmed. Proceeding.")

                feats, spref = self.downloader.download_features(
                    svc_url, layer_id,
                    geom_filter=gf, sr_wkid=wk,
                    progress_cb=self._prog
                )

                if not feats:
                    self._log("  No features found. Skipping.")
                    continue

                ml = self.downloader.to_qgis_layer(feats, spref, linfo)
                if ml is None or ml.featureCount() == 0:
                    self._log("  Conversion failed. Skipping.")
                    continue

                out_path = output
                gpkg_layer_name = linfo.get('name', layer_name)
                self.downloader.save_to_gpkg(
                    ml, out_path, gpkg_layer_name
                )
                self._log(
                    f"  Saved {ml.featureCount()} features: "
                    f"{gpkg_layer_name}"
                )

                if self.chk_add_map.isChecked():
                    self.downloader.load_gpkg_to_map(
                        out_path, gpkg_layer_name
                    )
                    self._log("  Added to map.")

                success_count += 1

            except Exception as ex:
                self._log(f"  ERROR: {ex}")

        total = len(items_to_download)
        summary_parts = [f"{success_count}/{total} layers downloaded"]
        if skipped_by_safety:
            summary_parts.append(
                f"{skipped_by_safety} skipped (safety)"
            )
        summary_msg = ", ".join(summary_parts)

        self._log(f"\nComplete: {summary_msg}")
        self.progress.setFormat("Complete!")
        self.btn_download.setEnabled(True)

        if success_count > 0:
            QMessageBox.information(
                self, "Download Complete",
                f"{summary_msg}\n\nOutput: {output}"
            )
        elif skipped_by_safety == total:
            QMessageBox.information(
                self, "All Skipped",
                "All layers were skipped by safety checks. "
                "Try zooming in or using a clip layer."
            )


# =====================================================================
# LAUNCH FUNCTION
# =====================================================================
def launch():
    """Launch GeoGrab. Call from QGIS Python Console."""
    try:
        _geograb_dlg.close()
        del globals()['_geograb_dlg']
    except Exception:
        pass

    import builtins
    try:
        builtins._geograb_dlg.close()
    except Exception:
        pass

    dlg = GeoGrabDialog()
    builtins._geograb_dlg = dlg
    dlg.show()
    dlg.raise_()
    dlg.activateWindow()
    return dlg
