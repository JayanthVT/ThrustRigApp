# Thrust Dashboard — PyQt6 skeleton

Proof-of-concept port of the Streamlit app's shell.

## What's here
- `main.py` — MainWindow: sidebar library list + ideaForge logo, Import Log
  button, hosts all tabs, global "Update Parameters" save button
- `dashboard_tab.py` — Test Summary + RPM lookup + live Plotly Thrust chart
- `measurable_tab.py` — steady-state window auto-detection + manual
  torque/thrust efficiency calculator (session-only, not persisted — matches
  the original)
- `initial_params_tab.py` — Initial Parameters form, same default/merge logic
- `test_check_tab.py` — Test Parameter Check, using `QTableWidget` instead of
  a manually-keyed loop. This is the fix for the original delete-row bug:
  Qt owns row identity natively (`removeRow(row)` acts on the actual row),
  so the whole "wrong row gets deleted" bug class can't happen here. Verified
  by scripted test — deleting a middle row and the last row both work correctly.
- `results_tab.py` — Results form, same max/abs-max computations from the log
- `python_functions/db.py`, `data_pipeline.py`, `charts.py` — copied
  **unchanged** from the Streamlit repo.
- `assets/ideaforge-logo.jpeg` — sidebar logo
- `assets/app_icon.ico` — window/taskbar/exe icon (generated from the logo)
- `build_exe.bat` — builds a standalone Windows .exe (see below)

## Run (development)
```
pip install -r requirements.txt
python main.py
```

Click "Import Log" to load a .csv/.xlsx test log — runs the same
load → normalize → parse_time → clean_and_drop → efficiency-column
pipeline as the Streamlit app, then renders metrics + RPM lookup +
a Plotly Thrust-vs-Time chart (embedded via QWebEngineView).

Saved runs show up in the left sidebar (same SQLite db, `thrust_logs.db`,
created next to main.py on first run).

## Build a standalone .exe (Windows only)

PyInstaller builds are platform-specific — you must run this **on Windows**,
it can't be cross-built from Linux/Mac.

```
build_exe.bat
```

This installs PyInstaller if needed and produces `dist\ThrustDashboard.exe`
— a single file with the ideaForge icon, no Python install required to run it.

Double-click it or pin it to your taskbar/desktop like any other app.

Important: the .exe keeps its database (`thrust_logs.db`) and imported
logs (`logs\`) in the **same folder as the .exe itself**, not in a temp
folder — so your saved runs persist between launches. Keep the .exe in
a folder you control (not e.g. Downloads if you plan to delete that later).

## Verified
Ran headlessly end-to-end with a synthetic 500-row log covering every
column all five tabs use: file load, cleaning pipeline, efficiency
column, Dashboard metrics + chart, Measurable Parameters window
auto-detection + calculate, Initial Parameters + Results form
population, Test Parameter Check default rows (12), and — the
original bug — **scripted deletion of a middle row and the last row,
both confirmed to remove the correct row and leave everything else
intact**. Also verified Update Parameters saves to SQLite and a
reload pulls the saved values back correctly.

## Not yet ported
The custom plot builder (multi-series overlay plots), saved-plot
gallery, downloads/PDF export, and the Explorer/library browsing
view (folders, search, rename, move). Those are the next chunks.
