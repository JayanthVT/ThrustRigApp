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

"""
plotly_asset.py — resolves the bundled plotly.min.js for fully-local,
network-free chart rendering.

THE ACTUAL BUG (confirmed, not guessed): QWebEngineView.setHtml(html) with
no baseUrl gives the loaded page no real origin. Chromium then blocks that
page from loading local file:// resources via <script src="file://...">
— "Not allowed to load local resource" — regardless of whether the file
exists. This is a security restriction, not a missing-file problem, and
it's why switching from a CDN <script> (always allowed, any origin) to a
local file:// reference broke chart rendering entirely.

THE FIX: pass a file:// baseUrl (pointing at the assets folder) as the
second argument to setHtml(). That gives the page a real file:// origin,
and it's then allowed to load sibling local file:// resources normally.
Verified directly: without baseUrl, `typeof Plotly` was "undefined" with
a SCRIPT LOAD ERROR in the console; with baseUrl set, it's "object".

Callers must use:
    self.plot_view.setHtml(html, get_assets_base_url())
NOT just setHtml(html) — the baseUrl argument is what makes this work.
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QUrl


def _assets_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent
    return base / "assets"


def get_plotly_js_path() -> Path:
    return _assets_dir() / "plotly.min.js"


def plotly_js_status() -> tuple[bool, str]:
    """(found_locally, path) — for diagnostics/status messages."""
    p = get_plotly_js_path()
    return p.exists(), str(p)


def get_assets_base_url() -> QUrl:
    """Pass this as the baseUrl argument to setHtml(). Gives the loaded
    page a file:// origin so it's allowed to load sibling local files
    like plotly.min.js — this is the fix, not optional."""
    return QUrl.fromLocalFile(str(_assets_dir()) + "/")


def get_plotly_script_tag() -> str:
    """Relative src works because callers pass get_assets_base_url() as
    setHtml()'s baseUrl — the browser resolves 'plotly.min.js' against
    that base, same as a normal web page resolving a relative URL."""
    return '<script src="plotly.min.js"></script>'
