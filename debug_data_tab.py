"""
debug_data_tab.py — Debug Log + Data Tables tab (PyQt6)

Port of app.py's show_debug / show_raw / show_raw_original toggles.
Same pipeline log messages (from data_pipeline.py's shared `logs` list),
same Cleaned-vs-Original distinction (df_raw = copy taken before
normalize_columns runs), same MM:SS.mmm Time formatting on the cleaned view.

Adds table tools on top of the plain QTableWidget: click-to-sort columns
(numeric-aware — a plain QTableWidgetItem sorts "10" before "2" since it
compares as text) and a search box that filters rows by substring match
across every column.
"""

import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QTableWidget, QTableWidgetItem, QStackedWidget, QLineEdit
)

MAX_DISPLAY_ROWS = 5000  # Qt's QTableWidget is far slower than st.dataframe at scale


def _fmt_ts(t):
    try:
        t = float(t)
        mins = int(t // 60)
        secs = t % 60
        ms = int(round((secs % 1) * 1000))
        return f"{mins:02d}:{int(secs):02d}.{ms:03d}"
    except Exception:
        return str(t)


class _SortableItem(QTableWidgetItem):
    """A plain QTableWidgetItem sorts everything as text — "10" ends up
    before "2", and the MM:SS.ms-formatted Time column would sort
    completely out of chronological order. This carries the real
    underlying numeric value alongside the display text, so clicking a
    column header sorts it properly regardless of formatting."""

    def __init__(self, text: str, sort_key=None):
        super().__init__(text)
        self._sort_key = sort_key

    def __lt__(self, other):
        if (
            isinstance(other, _SortableItem)
            and self._sort_key is not None
            and other._sort_key is not None
        ):
            try:
                return float(self._sort_key) < float(other._sort_key)
            except (TypeError, ValueError):
                pass
        return super().__lt__(other)


class DebugDataTab(QWidget):
    def __init__(self):
        super().__init__()
        self.df_clean: pd.DataFrame | None = None
        self.df_raw: pd.DataFrame | None = None

        root = QVBoxLayout(self)

        # ── Debug log ──
        root.addWidget(QLabel("🔍 Debug log"))
        self.debug_text = QTextEdit()
        self.debug_text.setReadOnly(True)
        self.debug_text.setStyleSheet(
            "background:#0a0c10; color:#9ca3af; font-family:'Consolas','Space Mono',monospace; "
            "font-size:12px; border:1px solid #2a2d3a; border-radius:6px;"
        )
        self.debug_text.setMaximumHeight(160)
        root.addWidget(self.debug_text)

        # ── Data table toggle + search ──
        toggle_row = QHBoxLayout()
        self.clean_btn = QPushButton("Cleaned data table")
        self.raw_btn = QPushButton("Original raw data")
        self.clean_btn.clicked.connect(lambda: self._show_table(0))
        self.raw_btn.clicked.connect(lambda: self._show_table(1))
        toggle_row.addWidget(self.clean_btn)
        toggle_row.addWidget(self.raw_btn)
        toggle_row.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Filter rows…")
        self.search_box.setMaximumWidth(240)
        self.search_box.textChanged.connect(self._apply_filter)
        toggle_row.addWidget(self.search_box)
        root.addLayout(toggle_row)

        self.caption = QLabel("")
        self.caption.setStyleSheet("color:#6b7280; font-size:11px;")
        root.addWidget(self.caption)

        self.stack = QStackedWidget()
        self.clean_table = QTableWidget()
        self.raw_table = QTableWidget()
        for t in (self.clean_table, self.raw_table):
            t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            t.setAlternatingRowColors(True)
            t.setSortingEnabled(True)
        self.stack.addWidget(self.clean_table)
        self.stack.addWidget(self.raw_table)
        root.addWidget(self.stack, stretch=1)

    def load_run(self, df_clean: pd.DataFrame, df_raw: pd.DataFrame, logs: list):
        self.df_clean = df_clean
        self.df_raw = df_raw
        self.debug_text.setPlainText("\n".join(logs))
        self.search_box.clear()
        self._populate_table(self.clean_table, df_clean, format_time=True)
        self._populate_table(self.raw_table, df_raw, format_time=False)
        self._show_table(0)

    def _show_table(self, index: int):
        self.stack.setCurrentIndex(index)
        if index == 0 and self.df_clean is not None:
            self.caption.setText(
                f"{len(self.df_clean):,} rows × {self.df_clean.shape[1]} cols — "
                f"column names normalised, Time shown as MM:SS.ms, NaN rows dropped"
                + (f"  (showing first {MAX_DISPLAY_ROWS:,})" if len(self.df_clean) > MAX_DISPLAY_ROWS else "")
            )
        elif index == 1 and self.df_raw is not None:
            self.caption.setText(
                f"{len(self.df_raw):,} rows × {self.df_raw.shape[1]} cols — "
                f"exactly as loaded from file, no changes"
                + (f"  (showing first {MAX_DISPLAY_ROWS:,})" if len(self.df_raw) > MAX_DISPLAY_ROWS else "")
            )
        self._apply_filter(self.search_box.text())

    def _apply_filter(self, text: str):
        table = self.stack.currentWidget()
        if table is None or table.rowCount() == 0:
            return
        needle = text.strip().lower()
        n_cols = table.columnCount()
        visible_count = 0
        for r in range(table.rowCount()):
            if not needle:
                match = True
            else:
                match = False
                for c in range(n_cols):
                    item = table.item(r, c)
                    if item is not None and needle in item.text().lower():
                        match = True
                        break
            table.setRowHidden(r, not match)
            if match:
                visible_count += 1
        if needle:
            base = self.caption.text().split(" — filtered")[0]
            self.caption.setText(f"{base} — filtered to {visible_count:,} row(s)")

    def _populate_table(self, table: QTableWidget, df: pd.DataFrame, format_time: bool):
        table.setSortingEnabled(False)  # avoid rows shuffling mid-populate
        if df is None or df.empty:
            table.setRowCount(0)
            table.setColumnCount(0)
            table.setSortingEnabled(True)
            return

        display_df = df.reset_index(drop=True)
        if len(display_df) > MAX_DISPLAY_ROWS:
            display_df = display_df.iloc[:MAX_DISPLAY_ROWS]

        cols = list(display_df.columns)
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels([str(c) for c in cols])
        table.setRowCount(len(display_df))

        time_col_idx = cols.index("Time") if (format_time and "Time" in cols) else None

        for r in range(len(display_df)):
            for c, col in enumerate(cols):
                val = display_df.iat[r, c]
                if c == time_col_idx:
                    text = _fmt_ts(val)
                    try:
                        sort_key = float(val)
                    except (TypeError, ValueError):
                        sort_key = None
                else:
                    text = "" if pd.isna(val) else str(val)
                    try:
                        sort_key = float(val) if not pd.isna(val) else None
                    except (TypeError, ValueError):
                        sort_key = None
                table.setItem(r, c, _SortableItem(text, sort_key=sort_key))

        table.resizeColumnsToContents()
        table.setSortingEnabled(True)
