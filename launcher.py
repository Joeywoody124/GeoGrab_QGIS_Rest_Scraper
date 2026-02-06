##########################################################################
# GeoGrab Launcher for QGIS
# ==========================
# Run this from the QGIS Python Console:
#
#   exec(open(r'E:\CLAUDE_Workspace\Claude\Report_Files\Projects\Rest_Scraper_QGIS\launcher.py', encoding='utf-8').read())
#
# Or open in the Script Editor (right panel) and click Run.
##########################################################################

import sys
import os
import shutil

# Add the project root to Python path so imports work
PROJECT_ROOT = r'E:\CLAUDE_Workspace\Claude\Report_Files\Projects\Rest_Scraper_QGIS'
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ------------------------------------------------------------------
# Clean __pycache__ folders to prevent stale bytecode after edits.
# This ensures code changes take effect without manual cleanup.
# ------------------------------------------------------------------
_pkg_root = os.path.join(PROJECT_ROOT, 'sc_rest_scraper')
for dirpath, dirnames, _ in os.walk(_pkg_root):
    if '__pycache__' in dirnames:
        cache_dir = os.path.join(dirpath, '__pycache__')
        try:
            shutil.rmtree(cache_dir)
        except Exception:
            pass  # Non-critical; proceed even if cleanup fails

# Force reimport if modules were already loaded (for development)
mods_to_reload = [k for k in sys.modules if k.startswith('sc_rest_scraper')]
for mod in mods_to_reload:
    del sys.modules[mod]

# Import and launch
from sc_rest_scraper.gui.main_dialog import launch

launch()
print("GeoGrab launched successfully.")
