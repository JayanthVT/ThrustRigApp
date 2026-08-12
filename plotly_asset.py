"""
plotly_asset.py — resolves the bundled plotly.min.js as a file:// URL.

Both dashboard_tab.py and plots_tab.py were using fig.to_html(include_plotlyjs="cdn"),
which makes QWebEngineView fetch Plotly.js from cdn.plot.ly on every single
setHtml() call — a full page reload, over the network, every time a chart
renders. On a slow/filtered network (common on a work laptop) that's exactly
where the visible "delay before the plot renders" comes from, and it fails
outright with no internet at all.

Fix: ship plotly.min.js locally (extracted once from the installed `plotly`
pip package — see assets/plotly.min.js) and point at it via a local file://
URL instead. No network dependency, consistent timing every time.
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QUrl


def get_plotly_js_url() -> str:
    """Returns a file:// URL string pointing at the bundled plotly.min.js."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent
    js_path = base / "assets" / "plotly.min.js"
    return QUrl.fromLocalFile(str(js_path)).toString()
