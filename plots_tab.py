"""
plots_tab.py — Custom Plot Builder + Saved Plots Gallery (PyQt6)

Port of view_plots.render_custom_plot() + render_saved_plots_gallery().
Same X/Y axis pickers (unlimited extra Y axes on the right), same Line/
Scatter toggle, same time-window filter, same down-sampling to ~5000 pts,
same dark Plotly styling with a range slider. Saved plots are rendered as
matplotlib PNGs (via the unmodified charts.fig_to_png) exactly like the
Streamlit version, since those PNGs are what goes into the PDF report —
session-only, same as the original (not written to SQLite).
"""

import matplotlib.pyplot as plt
import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QRadioButton, QButtonGroup, QCheckBox, QDoubleSpinBox, QLineEdit,
    QScrollArea, QFrame
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

from python_functions.charts import DARK, fig_to_png
from plotly_asset import get_plotly_js_url

_EXCLUDE = {"Thrust_0deg_kg", "Thrust_90deg_kg", "Thrust_180deg_kg",
            "Thrust_270deg_kg", "Total_Weight"}
_Y_COLOURS = ["#f97316", "#38bdf8", "#a78bfa", "#4ade80",
              "#fb923c", "#22d3ee", "#c084fc", "#86efac"]


class PlotsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.df: pd.DataFrame | None = None
        self.filename = None
        self.plot_cols = []
        self.extra_y_combos = []  # list of QComboBox for Y2, Y3, ...
        # {filename: [{"title","png","x","y"}, ...]}
        self._saved_plots: dict[str, list] = {}

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        root = QVBoxLayout(content)
        root.setSpacing(12)

        # ── Axis pickers ──
        axis_row = QHBoxLayout()
        axis_row.addWidget(QLabel("X axis"))
        self.x_combo = QComboBox()
        self.x_combo.currentIndexChanged.connect(self.render_plot)
        axis_row.addWidget(self.x_combo)

        axis_row.addWidget(QLabel("Y1 axis"))
        self.y_combo = QComboBox()
        self.y_combo.currentIndexChanged.connect(self.render_plot)
        axis_row.addWidget(self.y_combo)

        add_y_btn = QPushButton("＋ Y axis")
        add_y_btn.clicked.connect(self._add_extra_y)
        axis_row.addWidget(add_y_btn)

        rem_y_btn = QPushButton("－ Y axis")
        rem_y_btn.clicked.connect(self._remove_extra_y)
        axis_row.addWidget(rem_y_btn)
        axis_row.addStretch()
        root.addLayout(axis_row)

        self.extra_y_row = QHBoxLayout()
        root.addLayout(self.extra_y_row)
        self.extra_y_row.addStretch()

        # ── Controls ──
        ctrl_row = QHBoxLayout()
        ctrl_row.addWidget(QLabel("Type"))
        self.line_radio = QRadioButton("Line")
        self.scatter_radio = QRadioButton("Scatter")
        self.line_radio.setChecked(True)
        type_group = QButtonGroup(self)
        type_group.addButton(self.line_radio)
        type_group.addButton(self.scatter_radio)
        self.line_radio.toggled.connect(self.render_plot)
        ctrl_row.addWidget(self.line_radio)
        ctrl_row.addWidget(self.scatter_radio)

        self.window_check = QCheckBox("Time window")
        self.window_check.toggled.connect(self._on_window_toggled)
        ctrl_row.addWidget(self.window_check)

        ctrl_row.addWidget(QLabel("From (s)"))
        self.tmin_spin = QDoubleSpinBox()
        self.tmin_spin.setRange(0, 999999)
        self.tmin_spin.setEnabled(False)
        self.tmin_spin.valueChanged.connect(self.render_plot)
        ctrl_row.addWidget(self.tmin_spin)

        ctrl_row.addWidget(QLabel("To (s)"))
        self.tmax_spin = QDoubleSpinBox()
        self.tmax_spin.setRange(0, 999999)
        self.tmax_spin.setEnabled(False)
        self.tmax_spin.valueChanged.connect(self.render_plot)
        ctrl_row.addWidget(self.tmax_spin)
        ctrl_row.addStretch()
        root.addLayout(ctrl_row)

        # ── Plot ──
        self.plot_view = QWebEngineView()
        self.plot_view.setMinimumHeight(480)
        root.addWidget(self.plot_view)

        self.caption = QLabel("")
        self.caption.setStyleSheet("color:#6b7280; font-size:11px;")
        root.addWidget(self.caption)

        # ── Save plot ──
        save_row = QHBoxLayout()
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Plot title for report…")
        save_row.addWidget(self.title_edit, stretch=1)
        save_btn = QPushButton("💾 Save Plot")
        save_btn.clicked.connect(self.save_plot)
        save_row.addWidget(save_btn)
        root.addLayout(save_row)

        # ── Saved plots gallery ──
        root.addWidget(QLabel("📌 Saved Plots — these appear in the PDF report"))
        self.gallery_layout = QVBoxLayout()
        root.addLayout(self.gallery_layout)
        root.addStretch()

    # ── Load / setup ─────────────────────────────────────────
    def load_run(self, df: pd.DataFrame, filename: str):
        self.df = df
        self.filename = filename
        self.plot_cols = [
            c for c in df.columns
            if c not in _EXCLUDE and pd.api.types.is_numeric_dtype(df[c])
        ]

        self.x_combo.blockSignals(True)
        self.y_combo.blockSignals(True)
        self.x_combo.clear()
        self.y_combo.clear()
        self.x_combo.addItems(self.plot_cols)
        self.y_combo.addItems(self.plot_cols)
        x_default = "Time" if "Time" in self.plot_cols else (self.plot_cols[0] if self.plot_cols else "")
        y_default = "Thrust" if "Thrust" in self.plot_cols else (
            "RPM" if "RPM" in self.plot_cols else (self.plot_cols[1] if len(self.plot_cols) > 1 else ""))
        if x_default:
            self.x_combo.setCurrentText(x_default)
        if y_default:
            self.y_combo.setCurrentText(y_default)
        self.x_combo.blockSignals(False)
        self.y_combo.blockSignals(False)

        while self.extra_y_combos:
            self._remove_extra_y()

        tmax = float(df["Time"].max()) if "Time" in df.columns else 0.0
        for spin in (self.tmin_spin, self.tmax_spin):
            spin.blockSignals(True)
            spin.setMaximum(tmax)
            spin.blockSignals(False)
        self.tmin_spin.setValue(0.0)
        self.tmax_spin.setValue(tmax)

        self._refresh_gallery()
        self.render_plot()

    # ── Extra Y axes ─────────────────────────────────────────
    def _add_extra_y(self):
        combo = QComboBox()
        combo.addItems(["None"] + self.plot_cols)
        combo.currentIndexChanged.connect(self.render_plot)
        self.extra_y_combos.append(combo)
        idx = len(self.extra_y_combos)
        label = QLabel(f"Y{idx + 1} axis")
        combo.setProperty("_label_widget", label)
        # Insert before the trailing stretch (always the last item) so new
        # pairs append left-to-right and the row stays compact instead of
        # the label/combo splitting to fill the whole row width.
        insert_at = self.extra_y_row.count() - 1
        self.extra_y_row.insertWidget(insert_at, label)
        self.extra_y_row.insertWidget(insert_at + 1, combo)
        self.render_plot()

    def _remove_extra_y(self):
        if not self.extra_y_combos:
            return
        combo = self.extra_y_combos.pop()
        label = combo.property("_label_widget")
        self.extra_y_row.removeWidget(combo)
        combo.deleteLater()
        if label:
            self.extra_y_row.removeWidget(label)
            label.deleteLater()
        self.render_plot()

    def _on_window_toggled(self, checked):
        self.tmin_spin.setEnabled(checked)
        self.tmax_spin.setEnabled(checked)
        self.render_plot()

    def _active_extras(self):
        result = []
        for i, combo in enumerate(self.extra_y_combos):
            col = combo.currentText()
            if col and col != "None" and self.df is not None and col in self.df.columns:
                result.append((i, col))
        return result

    def _windowed_df(self):
        df = self.df
        if df is None:
            return None
        if self.window_check.isChecked() and "Time" in df.columns:
            df = df[(df["Time"] >= self.tmin_spin.value()) & (df["Time"] <= self.tmax_spin.value())]
        step = max(1, len(df) // 5000)
        return df.iloc[::step].copy()

    # ── Render (interactive Plotly) ─────────────────────────
    def render_plot(self, *_):
        if self.df is None or not self.plot_cols:
            return
        import plotly.graph_objects as go

        x_col = self.x_combo.currentText()
        y_col = self.y_combo.currentText()
        if not x_col or not y_col:
            return

        df_plot = self._windowed_df()
        active_extras = self._active_extras()
        plot_type = "Line" if self.line_radio.isChecked() else "Scatter"
        mode = "lines" if plot_type == "Line" else "markers"
        marker_size = 4 if plot_type == "Line" else 3

        fig = go.Figure()
        c1 = _Y_COLOURS[0]
        fig.add_trace(go.Scatter(
            x=df_plot[x_col], y=df_plot[y_col], mode=mode, name=y_col,
            line=dict(color=c1, width=1.6) if plot_type == "Line" else None,
            marker=dict(size=marker_size, color=c1), yaxis="y",
        ))
        for ei, ecol in active_extras:
            ec = _Y_COLOURS[(ei + 1) % len(_Y_COLOURS)]
            fig.add_trace(go.Scatter(
                x=df_plot[x_col], y=df_plot[ecol], mode=mode, name=ecol,
                line=dict(color=ec, width=1.4) if plot_type == "Line" else None,
                marker=dict(size=marker_size, color=ec), yaxis=f"y{ei + 2}",
            ))

        n_extra = len(active_extras)
        r_margin = max(60, 60 + n_extra * 60)
        x_domain = [0, max(0.60, 1.0 - n_extra * 0.10)]

        layout = dict(
            plot_bgcolor="#0d0f14", paper_bgcolor="#13161e",
            font=dict(color="#c8ccd8", family="monospace", size=11),
            xaxis=dict(
                title=dict(text=x_col, font=dict(color="#c8ccd8")),
                gridcolor="#1e2130", showline=True, linecolor="#2a2d3a",
                tickfont=dict(color="#6b7280"), domain=x_domain,
                rangeslider=dict(visible=True, thickness=0.06),
            ),
            yaxis=dict(
                title=dict(text=y_col, font=dict(color=c1)),
                tickfont=dict(color=c1), gridcolor="#1e2130",
                showline=True, linecolor="#2a2d3a",
            ),
            legend=dict(bgcolor="#13161e", bordercolor="#2a2d3a", borderwidth=1,
                        font=dict(color="#c8ccd8")),
            margin=dict(l=60, r=r_margin, t=30, b=50),
            hovermode="x unified", height=480,
        )
        for ei, ecol in active_extras:
            ec = _Y_COLOURS[(ei + 1) % len(_Y_COLOURS)]
            pos = round(1.0 - ei * 0.10, 2)
            layout[f"yaxis{ei + 2}"] = dict(
                title=dict(text=ecol, font=dict(color=ec)),
                tickfont=dict(color=ec), overlaying="y", side="right",
                anchor="free", position=pos, showgrid=False,
                showline=True, linecolor="#2a2d3a",
            )
        fig.update_layout(**layout)

        html = f"""
        <html><head>
            <script src="{get_plotly_js_url()}"></script>
            <style>html,body{{background:#0d0f14;margin:0;padding:0;}}</style>
        </head>
        <body>{fig.to_html(include_plotlyjs=False, full_html=False)}</body></html>
        """
        self.plot_view.setHtml(html)

        extras_txt = "".join(f"  |  Y{i+2}: {c}" for i, c in active_extras)
        self.caption.setText(f"X: {x_col}  |  Y1: {y_col}{extras_txt}  |  ({len(df_plot):,} pts)")

        extra_names = " & ".join(c for _, c in active_extras)
        auto_title = f"{y_col} vs {x_col}" + (f" & {extra_names}" if extra_names else "")
        if not self.title_edit.text() or getattr(self, "_auto_title_active", True):
            self.title_edit.setText(auto_title)
            self._auto_title_active = True

    # ── Save plot (matplotlib PNG, for PDF) ─────────────────
    def save_plot(self):
        if self.df is None or not self.filename:
            return
        x_col = self.x_combo.currentText()
        y_col = self.y_combo.currentText()
        active_extras = self._active_extras()
        df_plot = self._windowed_df()
        c1 = _Y_COLOURS[0]

        with plt.style.context(DARK):
            fig, ax1 = plt.subplots(figsize=(11, 3.4))
            ax1.plot(df_plot[x_col], df_plot[y_col], color=c1, linewidth=1.4, label=y_col)
            ax1.set_xlabel(x_col, fontsize=8)
            ax1.set_ylabel(y_col, color=c1, fontsize=8)
            ax1.tick_params(axis="y", colors=c1)
            prev_ax = ax1
            for ei, ecol in active_extras:
                ec = _Y_COLOURS[(ei + 1) % len(_Y_COLOURS)]
                axi = prev_ax.twinx()
                if ei > 0:
                    axi.spines["right"].set_position(("axes", 1.0 + ei * 0.12))
                axi.plot(df_plot[x_col], df_plot[ecol], color=ec, linewidth=1.2, label=ecol)
                axi.set_ylabel(ecol, color=ec, fontsize=8)
                axi.tick_params(axis="y", colors=ec)
                prev_ax = axi
            fig.legend(loc="upper left", fontsize=8, bbox_to_anchor=(0.08, 0.95))
            fig.tight_layout()
        png = fig_to_png(fig)

        title = self.title_edit.text().strip() or f"{y_col} vs {x_col}"
        plots = self._saved_plots.setdefault(self.filename, [])
        existing = next((p for p in plots if p["title"] == title), None)
        if existing:
            existing["png"] = png
        else:
            plots.append({"title": title, "png": png, "x": x_col, "y": y_col})
        self._refresh_gallery()

    def get_saved_plots(self, filename: str) -> list:
        """Returns [(title, png_bytes), ...] for PDF assembly."""
        return [(p["title"], p["png"]) for p in self._saved_plots.get(filename, [])]

    # ── Gallery ──────────────────────────────────────────────
    def _refresh_gallery(self):
        while self.gallery_layout.count():
            item = self.gallery_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        plots = self._saved_plots.get(self.filename, []) if self.filename else []
        if not plots:
            empty = QLabel("No saved plots yet for this run.")
            empty.setStyleSheet("color:#6b7280; font-size:11px;")
            self.gallery_layout.addWidget(empty)
            return

        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt as _Qt
        for idx, p in enumerate(plots):
            card = QFrame()
            card.setStyleSheet("background:#161a24; border:1px solid #2b3040; border-radius:8px;")
            cv = QVBoxLayout(card)

            header = QHBoxLayout()
            title_lbl = QLabel(f"{idx + 1}. {p['title']}")
            title_lbl.setStyleSheet("color:#e6e6e6; font-weight:600;")
            header.addWidget(title_lbl, stretch=1)
            rm_btn = QPushButton("🗑 Remove")
            rm_btn.clicked.connect(lambda _, t=p["title"]: self._remove_plot(t))
            header.addWidget(rm_btn)
            cv.addLayout(header)

            img_lbl = QLabel()
            pix = QPixmap()
            pix.loadFromData(p["png"])
            img_lbl.setPixmap(pix.scaledToWidth(700, _Qt.TransformationMode.SmoothTransformation))
            cv.addWidget(img_lbl)

            self.gallery_layout.addWidget(card)

    def _remove_plot(self, title: str):
        plots = self._saved_plots.get(self.filename, [])
        self._saved_plots[self.filename] = [p for p in plots if p["title"] != title]
        self._refresh_gallery()
