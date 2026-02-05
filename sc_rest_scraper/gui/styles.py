"""
styles.py - QSS Stylesheet for GeoGrab
========================================
Professional theme for GIS applications.
Three options: DARK, MEDIUM (default), LIGHT.
Applied to the main dialog for a polished, branded look.
"""

# =====================================================================
# MEDIUM THEME (default) - Lighter than original dark, still modern
# =====================================================================
COLORS_MEDIUM = {
    'bg_dark': '#2d2d3d',       # Main background (was #1e1e2e)
    'bg_medium': '#363648',     # Group boxes, tab pane (was #282840)
    'bg_light': '#42425a',      # Buttons, headers (was #313150)
    'bg_input': '#4d4d6a',      # Input fields (was #3b3b5c)
    'accent': '#4fc3f7',
    'accent_hover': '#81d4fa',
    'accent_dark': '#0288d1',
    'success': '#66bb6a',
    'success_hover': '#81c784',
    'warning': '#ffa726',
    'error': '#ef5350',
    'text_primary': '#ececec',   # Brighter text (was #e0e0e0)
    'text_secondary': '#b0b0b0', # Brighter muted (was #9e9e9e)
    'text_bright': '#ffffff',
    'border': '#5c5c7a',        # Lighter borders (was #4a4a6a)
    'border_focus': '#4fc3f7',
}

# =====================================================================
# DARK THEME (original, kept for reference / toggle)
# =====================================================================
COLORS_DARK = {
    'bg_dark': '#1e1e2e',
    'bg_medium': '#282840',
    'bg_light': '#313150',
    'bg_input': '#3b3b5c',
    'accent': '#4fc3f7',
    'accent_hover': '#81d4fa',
    'accent_dark': '#0288d1',
    'success': '#66bb6a',
    'success_hover': '#81c784',
    'warning': '#ffa726',
    'error': '#ef5350',
    'text_primary': '#e0e0e0',
    'text_secondary': '#9e9e9e',
    'text_bright': '#ffffff',
    'border': '#4a4a6a',
    'border_focus': '#4fc3f7',
}


def _build_stylesheet(colors):
    """Generate QSS from a color dictionary."""
    return """
QDialog {
    background-color: %(bg_dark)s;
    color: %(text_primary)s;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 9pt;
}

QGroupBox {
    background-color: %(bg_medium)s;
    border: 1px solid %(border)s;
    border-radius: 6px;
    margin-top: 12px;
    padding: 14px 10px 10px 10px;
    font-weight: bold;
    color: %(accent)s;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: %(accent)s;
}

QLabel {
    color: %(text_primary)s;
    padding: 2px 0;
}

QComboBox {
    background-color: %(bg_input)s;
    color: %(text_primary)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    padding: 6px 10px;
    min-height: 24px;
}
QComboBox:hover {
    border-color: %(border_focus)s;
}
QComboBox:focus {
    border-color: %(accent)s;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: %(bg_light)s;
    color: %(text_primary)s;
    selection-background-color: %(accent_dark)s;
    selection-color: %(text_bright)s;
    border: 1px solid %(border)s;
}

QLineEdit {
    background-color: %(bg_input)s;
    color: %(text_primary)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    padding: 6px 10px;
    min-height: 24px;
}
QLineEdit:hover {
    border-color: %(border_focus)s;
}
QLineEdit:focus {
    border-color: %(accent)s;
}

QPushButton {
    background-color: %(bg_light)s;
    color: %(text_primary)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    padding: 6px 16px;
    min-height: 28px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: %(accent_dark)s;
    border-color: %(accent)s;
    color: %(text_bright)s;
}
QPushButton:pressed {
    background-color: %(accent)s;
}
QPushButton:disabled {
    background-color: %(bg_medium)s;
    color: %(text_secondary)s;
    border-color: %(bg_light)s;
}

QPushButton#btn_download {
    background-color: %(success)s;
    color: %(bg_dark)s;
    font-size: 10pt;
    font-weight: bold;
    border: none;
    border-radius: 5px;
    padding: 8px 24px;
    min-height: 32px;
}
QPushButton#btn_download:hover {
    background-color: %(success_hover)s;
}
QPushButton#btn_download:disabled {
    background-color: %(bg_light)s;
    color: %(text_secondary)s;
}

QCheckBox {
    color: %(text_primary)s;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid %(border)s;
    border-radius: 3px;
    background-color: %(bg_input)s;
}
QCheckBox::indicator:checked {
    background-color: %(accent)s;
    border-color: %(accent)s;
}

QSpinBox {
    background-color: %(bg_input)s;
    color: %(text_primary)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 24px;
}

QProgressBar {
    background-color: %(bg_input)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    text-align: center;
    color: %(text_primary)s;
    min-height: 22px;
}
QProgressBar::chunk {
    background-color: %(accent)s;
    border-radius: 3px;
}

QTextEdit {
    background-color: %(bg_input)s;
    color: %(text_secondary)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    padding: 6px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 8pt;
}

QTabWidget::pane {
    background-color: %(bg_medium)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    top: -1px;
}
QTabBar::tab {
    background-color: %(bg_light)s;
    color: %(text_secondary)s;
    border: 1px solid %(border)s;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 20px;
    margin-right: 2px;
    font-weight: bold;
}
QTabBar::tab:selected {
    background-color: %(bg_medium)s;
    color: %(accent)s;
    border-bottom: 2px solid %(accent)s;
}
QTabBar::tab:hover:!selected {
    background-color: %(bg_medium)s;
    color: %(text_primary)s;
}

QTreeWidget {
    background-color: %(bg_input)s;
    color: %(text_primary)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    alternate-background-color: %(bg_light)s;
}
QTreeWidget::item:selected {
    background-color: %(accent_dark)s;
    color: %(text_bright)s;
}
QTreeWidget::item:hover {
    background-color: %(bg_light)s;
}

QHeaderView::section {
    background-color: %(bg_light)s;
    color: %(accent)s;
    border: 1px solid %(border)s;
    padding: 4px 8px;
    font-weight: bold;
}

QScrollBar:vertical {
    background-color: %(bg_dark)s;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: %(border)s;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: %(accent)s;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
""" % colors


# Build both themes
DARK_STYLESHEET = _build_stylesheet(COLORS_MEDIUM)  # Default is now MEDIUM
DARK_STYLESHEET_ORIG = _build_stylesheet(COLORS_DARK)  # Original if needed
