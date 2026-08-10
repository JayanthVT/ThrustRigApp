"""
main.py — Thrust Test Rig Dashboard (PyQt6 skeleton)

Proof-of-concept port of the Streamlit app's shell:
  - Sidebar: saved-run library (from python_functions/db.py, unchanged)
  - "Import Log" button -> QFileDialog -> same pipeline as Streamlit version
    (python_functions/data_pipeline.py, unchanged)
  - Main area: Dashboard tab (Test Summary + RPM lookup + a live Plotly chart,
    built on python_functions/charts.py, unchanged)

Run:
    python main.py

Everything under python_functions/ is copied verbatim from the Streamlit repo —
none of it imports streamlit, so none of it needed to change.
"""

import sys
import json
from pathlib import Path

import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QFileDialog,
    QTabWidget, QMessageBox, QSplitter, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap

from python_functions.db import (
    init_db, fetch_all_runs, fetch_run, save_run, update_init_params, update_result_params
)
from python_functions.data_pipeline import (
    load_file_from_path, normalize_columns, parse_time,
    clean_and_drop, extract_test_date, compute_stats
)
from dashboard_tab import DashboardTab
from initial_params_tab import InitialParametersTab
from results_tab import ResultsTab
from test_check_tab import TestCheckTab
from measurable_tab import MeasurableParametersTab

BASE_DIR = Path(__file__).parent

if getattr(sys, "frozen", False):
    # Running as a PyInstaller exe: assets are unpacked to a temp bundle dir
    # (sys._MEIPASS), but the DB/logs must live somewhere persistent —
    # next to the .exe itself — or they'd vanish when the app closes.
    ASSETS_DIR = Path(sys._MEIPASS) / "assets"
    APP_DIR = Path(sys.executable).parent
else:
    ASSETS_DIR = BASE_DIR / "assets"
    APP_DIR = BASE_DIR

LOGS_DIR = APP_DIR / "logs"
DB_PATH = APP_DIR / "thrust_logs.db"
LOGS_DIR.mkdir(exist_ok=True)

LOGO_PATH = ASSETS_DIR / "ideaforge-logo.jpeg"
ICON_PATH = ASSETS_DIR / "app_icon.ico"

DARK_QSS = """
QMainWindow, QWidget { background: #0d0f14; color: #e6e6e6; font-size: 14px; }
QLabel { background: transparent; }
QListWidget {
    background: #13161e; border: 1px solid #2a2d3a; border-radius: 8px;
    padding: 4px; font-size: 13px;
}
QListWidget::item { padding: 10px 8px; border-radius: 5px; margin: 1px 0; }
QListWidget::item:selected { background: #1c1f2e; color: #f97316; }
QLineEdit {
    background: #13161e; border: 1px solid #2a2d3a; border-radius: 6px;
    padding: 7px 10px; color: #e6e6e6; font-size: 13px;
}
QLineEdit:focus { border-color: #f97316; }
QPushButton {
    background: #1a1a2e; border: 1px solid #2f3342; border-radius: 7px;
    padding: 9px 14px; color: #e6e6e6; font-size: 13px; font-weight: 500;
}
QPushButton:hover { border-color: #f97316; color: #f97316; }
QPushButton:pressed { background: #14141f; }
QTabWidget::pane { border: 1px solid #2a2d3a; border-radius: 8px; top: -1px; }
QTabBar::tab {
    background: #13161e; color: #9ca3af; padding: 10px 20px;
    font-size: 13px; font-weight: 500;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
    margin-right: 2px;
}
QTabBar::tab:selected { background: #1a1a2e; color: #f97316; }
QTabBar::tab:hover:!selected { color: #d1d5db; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thrust Test Rig Dashboard")
        self.resize(1280, 820)
        self.setStyleSheet(DARK_QSS)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        init_db(DB_PATH)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(splitter)

        # ── Sidebar ──
        sidebar = QWidget()
        sv = QVBoxLayout(sidebar)
        sv.setContentsMargins(10, 10, 10, 10)

        brand = QLabel("ideaForge\nThrust Rig Dashboard")
        brand.setStyleSheet("font-size:13px; font-weight:600; color:#e0e0e0;")

        if LOGO_PATH.exists():
            logo_label = QLabel()
            pix = QPixmap(str(LOGO_PATH)).scaledToWidth(
                120, Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(pix)
            sv.addWidget(logo_label)

        sv.addWidget(brand)

        self.import_btn = QPushButton("📁 Import Log")
        self.import_btn.clicked.connect(self.import_log)
        sv.addWidget(self.import_btn)

        sv.addWidget(QLabel("Library"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search logs…")
        self.search_box.textChanged.connect(self._on_search_changed)
        sv.addWidget(self.search_box)

        self.library_list = QListWidget()
        self.library_list.itemClicked.connect(self.open_saved_run)
        sv.addWidget(self.library_list, stretch=1)

        splitter.addWidget(sidebar)

        # ── Main area (tabs) ──
        main_area = QWidget()
        main_v = QVBoxLayout(main_area)
        main_v.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.dashboard_tab = DashboardTab()
        self.measurable_tab = MeasurableParametersTab()
        self.initial_params_tab = InitialParametersTab()
        self.test_check_tab = TestCheckTab(db_path=DB_PATH)
        self.results_tab = ResultsTab()

        self.tabs.addTab(self.dashboard_tab, "📊 Dashboard")
        self.tabs.addTab(self.measurable_tab, "📐 Measurable Params")
        self.tabs.addTab(self.initial_params_tab, "🧪 Initial Params")
        self.tabs.addTab(self.test_check_tab, "✅ Test Parameter Check")
        self.tabs.addTab(self.results_tab, "📈 Results")

        main_v.addWidget(self.tabs, stretch=1)

        save_row = QHBoxLayout()
        self.update_btn = QPushButton("💾 Update Parameters")
        self.update_btn.clicked.connect(self.update_parameters)
        self.update_btn.setEnabled(False)
        save_row.addWidget(self.update_btn)
        self.save_status = QLabel("")
        self.save_status.setStyleSheet("color:#22c55e; font-size:11px;")
        save_row.addWidget(self.save_status)
        save_row.addStretch()
        main_v.addLayout(save_row)

        splitter.addWidget(main_area)

        splitter.setSizes([260, 1020])

        self.statusBar().showMessage("Ready")
        self.current_filename = None
        self._refresh_library()

    # ── Library sidebar ─────────────────────────────────────
    def _refresh_library(self, search_text: str = ""):
        self.library_list.clear()
        runs = fetch_all_runs(search_text=search_text, db_path=DB_PATH)
        if not runs:
            msg = "No runs match your search." if search_text else "No saved runs yet."
            item = QListWidgetItem(msg)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.library_list.addItem(item)
            return
        for r in runs:
            item = QListWidgetItem(r["display_name"])
            item.setData(Qt.ItemDataRole.UserRole, r["filename"])
            self.library_list.addItem(item)

    def _on_search_changed(self, text: str):
        self._refresh_library(search_text=text.strip())

    def open_saved_run(self, item: QListWidgetItem):
        filename = item.data(Qt.ItemDataRole.UserRole)
        if not filename:
            return
        run_meta = fetch_run(filename, DB_PATH)
        if not run_meta or not run_meta.get("file_path") or not Path(run_meta["file_path"]).exists():
            QMessageBox.warning(self, "Missing file", "File was moved or deleted.")
            return
        self._load_and_show(Path(run_meta["file_path"]), filename)

    # ── Import flow ──────────────────────────────────────────
    def import_log(self):
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Import test log", str(LOGS_DIR),
            "Log files (*.csv *.xlsx *.xls);;All files (*.*)"
        )
        if not path_str:
            return
        src = Path(path_str)
        dest = LOGS_DIR / src.name
        if src.resolve() != dest.resolve():
            dest.write_bytes(src.read_bytes())

        df = self._load_and_show(dest, dest.name)
        if df is None:
            return

        # Save to library, same as Streamlit's "Update" button flow
        stats = compute_stats(df)
        test_date = extract_test_date(dest.name)
        save_run(dest.name, dest.stem, test_date, dest, stats, {}, folder="Uncategorised", db_path=DB_PATH)
        self._refresh_library(search_text=self.search_box.text().strip())
        self.statusBar().showMessage(f"Imported and saved: {dest.name}", 5000)

    # ── Shared load pipeline ─────────────────────────────────
    def _load_and_show(self, file_path: Path, filename: str):
        logs = []
        df = load_file_from_path(file_path, logs)
        if df is None:
            QMessageBox.critical(self, "Load failed", "Could not parse the file.\n\n" + "\n".join(logs))
            return None

        df = normalize_columns(df, logs)
        df = parse_time(df, logs)
        df = clean_and_drop(df, logs)

        if all(c in df.columns for c in ["Thrust", "Voltage", "Current"]):
            p_elec = df["Voltage"] * df["Current"]
            df["Overall_Efficiency_gW"] = (
                (df["Thrust"] * 101.972) / p_elec
            ).replace([np.inf, -np.inf], np.nan)

        if df.empty:
            QMessageBox.warning(self, "Empty data", "DataFrame is empty after cleaning.")
            return None

        self.current_filename = filename
        self.update_btn.setEnabled(True)
        self.save_status.setText("")

        # Pull any previously-saved JSON blobs for this run
        db_row = fetch_run(filename, DB_PATH) or {}
        saved_ip = self._safe_json(db_row.get("init_params"))
        saved_rp = self._safe_json(db_row.get("result_params"))
        saved_tpc = self._safe_json(db_row.get("test_param_check"), default=[])

        self.dashboard_tab.load_dataframe(df)
        self.measurable_tab.load_run(df)
        self.initial_params_tab.load_run(df, filename, saved_ip)
        self.results_tab.load_run(df, filename, saved_rp)
        self.test_check_tab.load_run(filename, saved_tpc)

        self.statusBar().showMessage(f"Loaded {filename} — {len(df):,} rows", 5000)
        return df

    @staticmethod
    def _safe_json(raw, default=None):
        if not raw:
            return default if default is not None else {}
        try:
            return json.loads(raw)
        except Exception:
            return default if default is not None else {}

    def update_parameters(self):
        """Mirrors the Streamlit app's bottom-of-page 'Update' button:
        persists Initial Params + Results together. Test Parameter Check
        has its own Save button since it did in the original too."""
        if not self.current_filename:
            return
        update_init_params(self.current_filename, self.initial_params_tab.get_values(), db_path=DB_PATH)
        update_result_params(self.current_filename, self.results_tab.get_values(), db_path=DB_PATH)
        self.save_status.setText("✅ Saved.")
        self.statusBar().showMessage("Parameters updated.", 4000)


def main():
    app = QApplication(sys.argv)
    if ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(ICON_PATH)))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
