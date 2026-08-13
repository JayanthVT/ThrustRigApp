# Thrust Dashboard 

A PyQt6 desktop app for reviewing thrust-rig test logs: import a CSV/XLSX
log, browse metrics, build custom plots, and export a PDF or Word report.

## Tabs (in order)
- **📊 Dashboard** — Test Summary metrics, RPM Lookup, and a Thrust-vs-Time
  chart (falls back to RPM-vs-Time when a log has no Thrust column)
- **🧪 Initial Params** — Initial Parameters form + free-text Observations
- **📈 Results** — max/peak values pulled from the log, editable
- **✅ Checklist** — Test Parameter Check, pass/fail rows against criteria
  (`QTableWidget`-based — deleting a row acts on the actual row, not an
  index, so there's no "wrong row gets deleted" bug class here)
- **📋 Raw Data Table** — full raw dataframe for the loaded log
- **📉 Plot Builder** — build custom multi-axis plots (X/Y1/Y2/Y3+, line or
  scatter, time-windowed), save snapshots for inclusion in reports
- **📐 Measurable Params** — steady-state window auto-detection + manual
  torque/thrust efficiency calculator (session-only, not persisted)
- **📄 PDF Report** — preview + download a PDF or Word report, with
  checkboxes to include/exclude each section (Initial Parameters —
  which also carries Observations, Test Parameter Check, Results,
  Measurable Params, Test Charts)

## Run (development)
```
pip install -r requirements.txt
python main.py
```

Click "Import Log" to load a .csv/.xlsx test log — runs the same
load → normalize → parse_time → clean_and_drop → efficiency-column
pipeline, then populates every tab.

Saved runs show up in the left sidebar (SQLite db, `thrust_logs.db`,
created next to `main.py` in development, or next to the `.exe` itself
once built — see below).

## Build a standalone .exe (Windows only)

PyInstaller builds are platform-specific — run this **on Windows**,
it can't be cross-built from Linux/Mac.

```
build_exe.bat
```

This installs PyInstaller if needed and produces
`dist\ThrustDashboard\ThrustDashboard.exe` (onedir build — launches
near-instantly, unlike a onefile build which has to unpack itself on
every launch).

Important: the .exe keeps its database (`thrust_logs.db`) and imported
logs (`logs\`) in the **same folder as the .exe itself**, not in a temp
folder — so your saved runs persist between launches. Keep the .exe in
a folder you control (not e.g. Downloads if you plan to delete that
later), and move the whole `ThrustDashboard` folder together if you
relocate it — the `.exe` needs the files sitting next to it.

## Project layout
- `main.py` — MainWindow: sidebar library list + ideaForge logo, Import
  Log button, hosts all tabs, global "Update Parameters" save button,
  assembles report data for PDF/DOCX export
- `dashboard_tab.py`, `initial_params_tab.py`, `results_tab.py`,
  `test_check_tab.py`, `debug_data_tab.py`, `plots_tab.py`,
  `measurable_tab.py` — one file per tab
- `pdf_tab.py` — PDF/DOCX preview + download UI, section include/exclude
  checkboxes
- `pdf_engine.py`, `docx_engine.py` — report builders (reportlab /
  python-docx), each takes the same data dict + a `sections` dict
- `card_style.py` — shared metric-card widget styling
- `plotly_asset.py` — resolves the bundled `assets/plotly.min.js` as a
  local file:// URL, so charts don't depend on internet access or a
  CDN fetch on every render
- `python_functions/db.py`, `data_pipeline.py`, `charts.py` — log
  loading/cleaning pipeline, SQLite persistence, chart helpers
- `assets/` — logo, app icon, bundled plotly.min.js
- `build_exe.bat`, `ThrustDashboard.spec` — PyInstaller build config
