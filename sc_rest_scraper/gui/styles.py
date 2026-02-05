"""
styles.py - QSS Stylesheet for GeoGrab
========================================
Theme options: SKETCH (default), MEDIUM, DARK.

SKETCH theme adapts the "Sketch / Hand-Drawn" design system
for Qt widgets -- warm paper backgrounds, soft pencil-black text,
thick borders, and a light approachable feel.

Qt QSS limitations vs the full Sketch spec:
  - No wobbly border-radius (Qt only supports uniform px values)
  - No Google Fonts (uses system fonts that approximate the feel)
  - No hard-offset box-shadows on most widgets (approximated where possible)
  - No per-element rotation

Applied to the main dialog for a polished, branded look.
"""

# =====================================================================
# SKETCH THEME (default) - Warm, light, paper-like
# =====================================================================
COLORS_SKETCH = {
    'bg_paper':       '#fdfbf7',   # Warm Paper - main background
    'bg_card':        '#ffffff',   # White - cards, group boxes
    'bg_muted':       '#f2efe9',   # Slightly tinted paper for depth
    'bg_input':       '#ffffff',   # Clean white inputs
    'bg_input_alt':   '#faf8f4',   # Alternating row tint
    'accent':         '#2d5da1',   # Blue Ballpoint Pen - primary actions
    'accent_hover':   '#3a6fb5',   # Lighter blue on hover
    'accent_dark':    '#1e4278',   # Pressed / selection
    'accent_red':     '#ff4d4d',   # Red Correction Marker - emphasis
    'success':        '#3a8a3e',   # Earthy green for download
    'success_hover':  '#4a9e4e',
    'warning':        '#d4880f',   # Warm amber
    'error':          '#d63b3b',   # Muted red
    'postit':         '#fff9c4',   # Post-it Yellow for highlights
    'text_primary':   '#2d2d2d',   # Soft Pencil Black (never pure black)
    'text_secondary': '#6b6b6b',   # Lighter pencil for secondary text
    'text_bright':    '#ffffff',   # White on dark backgrounds
    'border':         '#c5bfb3',   # Warm gray border (paper edge)
    'border_strong':  '#2d2d2d',   # Pencil-dark border for emphasis
    'border_focus':   '#2d5da1',   # Blue focus ring
}

# =====================================================================
# MEDIUM THEME - Darker option (previous default)
# =====================================================================
COLORS_MEDIUM = {
    'bg_paper':       '#2d2d3d',
    'bg_card':        '#363648',
    'bg_muted':       '#363648',
    'bg_input':       '#4d4d6a',
    'bg_input_alt':   '#42425a',
    'accent':         '#4fc3f7',
    'accent_hover':   '#81d4fa',
    'accent_dark':    '#0288d1',
    'accent_red':     '#ef5350',
    'success':        '#66bb6a',
    'success_hover':  '#81c784',
    'warning':        '#ffa726',
    'error':          '#ef5350',
    'postit':         '#fff9c4',
    'text_primary':   '#ececec',
    'text_secondary': '#b0b0b0',
    'text_bright':    '#ffffff',
    'border':         '#5c5c7a',
    'border_strong':  '#5c5c7a',
    'border_focus':   '#4fc3f7',
}

# =====================================================================
# DARK THEME (original)
# =====================================================================
COLORS_DARK = {
    'bg_paper':       '#1e1e2e',
    'bg_card':        '#282840',
    'bg_muted':       '#282840',
    'bg_input':       '#3b3b5c',
    'bg_input_alt':   '#313150',
    'accent':         '#4fc3f7',
    'accent_hover':   '#81d4fa',
    'accent_dark':    '#0288d1',
    'accent_red':     '#ef5350',
    'success':        '#66bb6a',
    'success_hover':  '#81c784',
    'warning':        '#ffa726',
    'error':          '#ef5350',
    'postit':         '#fff9c4',
    'text_primary':   '#e0e0e0',
    'text_secondary': '#9e9e9e',
    'text_bright':    '#ffffff',
    'border':         '#4a4a6a',
    'border_strong':  '#4a4a6a',
    'border_focus':   '#4fc3f7',
}


def _build_stylesheet(colors):
    """Generate QSS from a color dictionary."""
    return """
/* ============================================================
   GeoGrab QSS Theme
   ============================================================ */

QDialog {{
    background-color: {bg_paper};
    color: {text_primary};
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 9pt;
}}

/* ---- Group Boxes ---- */
QGroupBox {{
    background-color: {bg_card};
    border: 2px solid {border};
    border-radius: 8px;
    margin-top: 14px;
    padding: 16px 12px 12px 12px;
    font-weight: bold;
    color: {accent};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
    color: {accent};
    font-size: 9pt;
}}

/* ---- Labels ---- */
QLabel {{
    color: {text_primary};
    padding: 2px 0;
}}

/* ---- Combo Boxes ---- */
QComboBox {{
    background-color: {bg_input};
    color: {text_primary};
    border: 2px solid {border};
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 24px;
}}
QComboBox:hover {{
    border-color: {accent};
}}
QComboBox:focus {{
    border-color: {accent};
    border-width: 2px;
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {bg_card};
    color: {text_primary};
    selection-background-color: {accent};
    selection-color: {text_bright};
    border: 2px solid {border};
    border-radius: 4px;
}}

/* ---- Line Edits ---- */
QLineEdit {{
    background-color: {bg_input};
    color: {text_primary};
    border: 2px solid {border};
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 24px;
}}
QLineEdit:hover {{
    border-color: {accent};
}}
QLineEdit:focus {{
    border-color: {accent};
    border-width: 2px;
}}

/* ---- Buttons (General) ---- */
QPushButton {{
    background-color: {bg_card};
    color: {text_primary};
    border: 2px solid {border_strong};
    border-radius: 6px;
    padding: 6px 18px;
    min-height: 28px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {accent};
    border-color: {accent};
    color: {text_bright};
}}
QPushButton:pressed {{
    background-color: {accent_dark};
    border-color: {accent_dark};
    color: {text_bright};
}}
QPushButton:disabled {{
    background-color: {bg_muted};
    color: {text_secondary};
    border-color: {border};
}}

/* ---- Download Button (special) ---- */
QPushButton#btn_download {{
    background-color: {success};
    color: {text_bright};
    font-size: 10pt;
    font-weight: bold;
    border: 2px solid {success};
    border-radius: 6px;
    padding: 8px 24px;
    min-height: 32px;
}}
QPushButton#btn_download:hover {{
    background-color: {success_hover};
    border-color: {success_hover};
}}
QPushButton#btn_download:disabled {{
    background-color: {bg_muted};
    color: {text_secondary};
    border-color: {border};
}}

/* ---- Checkboxes ---- */
QCheckBox {{
    color: {text_primary};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {border_strong};
    border-radius: 4px;
    background-color: {bg_input};
}}
QCheckBox::indicator:checked {{
    background-color: {accent};
    border-color: {accent};
}}
QCheckBox::indicator:hover {{
    border-color: {accent};
}}

/* ---- Spin Boxes ---- */
QSpinBox {{
    background-color: {bg_input};
    color: {text_primary};
    border: 2px solid {border};
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 24px;
}}
QSpinBox:focus {{
    border-color: {accent};
}}

/* ---- Progress Bar ---- */
QProgressBar {{
    background-color: {bg_muted};
    border: 2px solid {border};
    border-radius: 6px;
    text-align: center;
    color: {text_primary};
    min-height: 22px;
    font-weight: bold;
}}
QProgressBar::chunk {{
    background-color: {accent};
    border-radius: 4px;
}}

/* ---- Log / Text Edit ---- */
QTextEdit {{
    background-color: {bg_input};
    color: {text_secondary};
    border: 2px solid {border};
    border-radius: 6px;
    padding: 8px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 8pt;
}}

/* ---- Tab Widget ---- */
QTabWidget::pane {{
    background-color: {bg_card};
    border: 2px solid {border};
    border-radius: 6px;
    top: -1px;
}}
QTabBar::tab {{
    background-color: {bg_muted};
    color: {text_secondary};
    border: 2px solid {border};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 20px;
    margin-right: 3px;
    font-weight: bold;
}}
QTabBar::tab:selected {{
    background-color: {bg_card};
    color: {accent};
    border-color: {border};
    border-bottom: 2px solid {bg_card};
}}
QTabBar::tab:hover:!selected {{
    background-color: {bg_card};
    color: {text_primary};
}}

/* ---- Tree Widget ---- */
QTreeWidget {{
    background-color: {bg_input};
    color: {text_primary};
    border: 2px solid {border};
    border-radius: 6px;
    alternate-background-color: {bg_input_alt};
    outline: none;
}}
QTreeWidget::item {{
    padding: 3px 0;
}}
QTreeWidget::item:selected {{
    background-color: {accent};
    color: {text_bright};
    border-radius: 3px;
}}
QTreeWidget::item:hover {{
    background-color: {bg_muted};
}}

/* ---- Header View ---- */
QHeaderView::section {{
    background-color: {bg_muted};
    color: {accent};
    border: 1px solid {border};
    padding: 4px 8px;
    font-weight: bold;
}}

/* ---- Scroll Bars ---- */
QScrollBar:vertical {{
    background-color: {bg_paper};
    width: 10px;
    border: none;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background-color: {border};
    border-radius: 5px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {accent};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background-color: {bg_paper};
    height: 10px;
    border: none;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background-color: {border};
    border-radius: 5px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {accent};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ---- Frames / Separators ---- */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {border};
}}

/* ---- Tooltips ---- */
QToolTip {{
    background-color: {postit};
    color: {text_primary};
    border: 2px solid {border_strong};
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 8pt;
}}

/* ---- List Widget ---- */
QListWidget {{
    background-color: {bg_input};
    color: {text_primary};
    border: 2px solid {border};
    border-radius: 6px;
    outline: none;
}}
QListWidget::item {{
    padding: 4px 6px;
}}
QListWidget::item:selected {{
    background-color: {accent};
    color: {text_bright};
}}
QListWidget::item:hover {{
    background-color: {bg_muted};
}}

/* ---- Message Box ---- */
QMessageBox {{
    background-color: {bg_paper};
    color: {text_primary};
}}
""".format(**colors)


# =====================================================================
# Build all themes
# =====================================================================
SKETCH_STYLESHEET = _build_stylesheet(COLORS_SKETCH)
MEDIUM_STYLESHEET = _build_stylesheet(COLORS_MEDIUM)
DARK_STYLESHEET_ORIG = _build_stylesheet(COLORS_DARK)

# Default export -- used by main_dialog.py
DARK_STYLESHEET = SKETCH_STYLESHEET
