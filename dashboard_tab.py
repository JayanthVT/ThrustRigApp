"""
dashboard_tab.py — Test Summary tab (PyQt6)

Direct port of view_dashboard.render_test_summary() from the Streamlit app.
Same metric computations, same RPM-lookup logic — just rendered as
QLabel grids + QSpinBox controls instead of st.metric()/st.number_input().
"""

import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QSpinBox, QGroupBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView

from python_functions.charts import pl_single
from card_style import metric_card


def _metric_widget(label: str, value: str, tooltip: str = ""):
    return metric_card(label, value, tooltip=tooltip)


def _raw_ts(df: pd.DataFrame, idx) -> str:
    try:
        t = df.loc[idx, "Time"]
        mins = int(t // 60)
        secs = t % 60
        return f"{mins:02d}:{secs:05.2f}"
    except Exception:
        return "—"


class DashboardTab(QWidget):
    """Test Summary + RPM Lookup, backed by a loaded DataFrame."""

    def __init__(self):
        super().__init__()
        self.df: pd.DataFrame | None = None

        root = QVBoxLayout(self)
        root.setSpacing(14)

        self.title = QLabel("📊 Test Summary")
        self.title.setStyleSheet("font-size:16px; font-weight:600; color:#e0e0e0;")
        root.addWidget(self.title)

        self.metrics_row = QHBoxLayout()
        self.metrics_row.setSpacing(10)
        root.addLayout(self.metrics_row)

        # ── RPM lookup controls ──
        lookup_box = QGroupBox("🔍 RPM Lookup")
        lookup_box.setStyleSheet(
            "QGroupBox { color:#e0e0e0; border:1px solid #2a2d3a; border-radius:8px; margin-top:8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left:10px; padding:0 4px; }"
        )
        lv = QVBoxLayout(lookup_box)

        ctrl_row = QHBoxLayout()
        ctrl_row.addWidget(QLabel("Target RPM"))
        self.rpm_spin = QSpinBox()
        self.rpm_spin.setRange(0, 200000)
        self.rpm_spin.setSingleStep(50)
        self.rpm_spin.valueChanged.connect(self._update_lookup)
        ctrl_row.addWidget(self.rpm_spin)

        ctrl_row.addSpacing(20)
        ctrl_row.addWidget(QLabel("Tolerance ±"))
        self.tol_spin = QSpinBox()
        self.tol_spin.setRange(1, 200)
        self.tol_spin.setValue(25)
        self.tol_spin.valueChanged.connect(self._update_lookup)
        ctrl_row.addWidget(self.tol_spin)
        ctrl_row.addStretch()
        lv.addLayout(ctrl_row)

        self.lookup_caption = QLabel("")
        self.lookup_caption.setStyleSheet("color:#6b7280; font-size:11px;")
        lv.addWidget(self.lookup_caption)

        self.lookup_row = QHBoxLayout()
        lv.addLayout(self.lookup_row)

        root.addWidget(lookup_box)

        # ── Thrust/RPM vs Time plot ──
        # (Plots Thrust vs Time when available, otherwise falls back to
        # RPM vs Time — most logs don't have a Thrust column, and RPM is
        # always present, so this is what actually renders in practice.
        # Plot Builder, for anything more flexible, lives in its own tab.)
        self.plot_view = QWebEngineView()
        self.plot_view.setMinimumHeight(380)
        root.addWidget(self.plot_view)

        root.addStretch()
        self._render_placeholder()
        # QWebEngineView's Chromium process isn't fully initialized the instant
        # the widget is constructed (before the window is shown) — a setHtml()
        # call made synchronously here can silently get dropped. Deferring by
        # one event-loop tick lets it finish initializing first.
        QTimer.singleShot(0, self._set_plot_placeholder)

    def _set_plot_placeholder(self):
        """Dark empty page instead of QWebEngineView's default white background."""
        self.plot_view.setHtml(
            "<html><body style='background:#0d0f14; margin:0;'></body></html>"
        )

    # ── Public API ──────────────────────────────────────────
    def load_dataframe(self, df: pd.DataFrame):
        self.df = df
        self._render_metrics()
        self._render_plot()
        if "RPM" in df.columns and not df.empty:
            peak_rpm = int(df["RPM"].max())
            self.rpm_spin.setMaximum(peak_rpm)
            self.rpm_spin.setValue(peak_rpm)
        self._update_lookup()

    # ── Internal renderers ──────────────────────────────────
    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _render_placeholder(self):
        self._clear_layout(self.metrics_row)
        self.metrics_row.addWidget(_metric_widget("Status", "No file loaded"))
        self.metrics_row.addStretch()

    def _render_metrics(self):
        df = self.df
        self._clear_layout(self.metrics_row)

        if "RPM" not in df.columns or df.empty:
            self.metrics_row.addWidget(_metric_widget(
                "Peak Thrust", f"{df['Thrust'].max():.1f} N" if "Thrust" in df.columns else "—"))
            self.metrics_row.addWidget(_metric_widget(
                "Max ESC Temp", f"{df['ESC_Temp'].max():.1f} °C" if "ESC_Temp" in df.columns else "—"))
            self.metrics_row.addWidget(_metric_widget(
                "Max Motor Temp", f"{df['Motor_Temp'].max():.1f} °C" if "Motor_Temp" in df.columns else "—"))
            self.metrics_row.addWidget(_metric_widget(
                "Duration", f"{df['Time'].max():.1f} s" if "Time" in df.columns else "—"))
            self.metrics_row.addStretch()
            return

        rpm_idx = df["RPM"].idxmax()
        peak_rpm = df.loc[rpm_idx, "RPM"]

        peak_thrust = df["Thrust"].max() if "Thrust" in df.columns else None
        thrust_idx = df["Thrust"].idxmax() if "Thrust" in df.columns else None
        max_esc = df["ESC_Temp"].max() if "ESC_Temp" in df.columns else None
        esc_idx = df["ESC_Temp"].idxmax() if "ESC_Temp" in df.columns else None
        max_motor = df["Motor_Temp"].max() if "Motor_Temp" in df.columns else None
        motor_idx = df["Motor_Temp"].idxmax() if "Motor_Temp" in df.columns else None
        peak_torque = df["Torque"].abs().max() if "Torque" in df.columns else None
        torque_idx = df["Torque"].abs().idxmax() if "Torque" in df.columns else None

        self.metrics_row.addWidget(_metric_widget(
            "Peak RPM", f"{int(peak_rpm):,}", f"Timestamp: {_raw_ts(df, rpm_idx)}"))
        self.metrics_row.addWidget(_metric_widget(
            "Peak Thrust", f"{peak_thrust:.1f} N" if peak_thrust is not None else "—",
            f"Timestamp: {_raw_ts(df, thrust_idx)}" if thrust_idx is not None else ""))
        self.metrics_row.addWidget(_metric_widget(
            "Peak Torque", f"{peak_torque:.2f} Nm" if peak_torque is not None else "—",
            f"Timestamp: {_raw_ts(df, torque_idx)}" if torque_idx is not None else ""))
        self.metrics_row.addWidget(_metric_widget(
            "Max ESC Temp", f"{max_esc:.1f} °C" if max_esc is not None else "—",
            f"Timestamp: {_raw_ts(df, esc_idx)}" if esc_idx is not None else ""))
        self.metrics_row.addWidget(_metric_widget(
            "Max Motor Temp", f"{max_motor:.1f} °C" if max_motor is not None else "—",
            f"Timestamp: {_raw_ts(df, motor_idx)}" if motor_idx is not None else ""))
        self.metrics_row.addStretch()

    def _update_lookup(self):
        self._clear_layout(self.lookup_row)
        df = self.df
        if df is None or "RPM" not in df.columns or df.empty:
            return

        lookup_rpm = self.rpm_spin.value()
        tol = self.tol_spin.value()
        band = df[(df["RPM"] >= lookup_rpm - tol) & (df["RPM"] <= lookup_rpm + tol)]

        if len(band) == 0:
            self.lookup_caption.setText(f"No data within ±{tol} RPM of {lookup_rpm}.")
            return

        lv = band["Voltage"].mean() if "Voltage" in band.columns else None
        li = band["Current"].mean() if "Current" in band.columns else None
        lpe = (lv * li) if (lv and li) else None
        lt = band["Thrust"].mean() if "Thrust" in band.columns else None
        ltor = band["Torque"].abs().mean() if "Torque" in band.columns else None
        lmt = band["Motor_Temp"].mean() if "Motor_Temp" in band.columns else None
        let = band["ESC_Temp"].mean() if "ESC_Temp" in band.columns else None
        lrpm = band["RPM"].mean()

        self.lookup_caption.setText(f"Mean over {len(band)} rows  |  actual RPM: {lrpm:.1f}")

        self.lookup_row.addWidget(_metric_widget("Actual RPM", f"{lrpm:.1f}"))
        self.lookup_row.addWidget(_metric_widget("DC Voltage", f"{lv:.1f} V" if lv is not None else "—"))
        self.lookup_row.addWidget(_metric_widget("Current", f"{li:.1f} A" if li is not None else "—"))
        self.lookup_row.addWidget(_metric_widget("Elec. Power", f"{lpe:.0f} W" if lpe is not None else "—"))
        self.lookup_row.addWidget(_metric_widget("Thrust", f"{lt:.1f} N" if lt is not None else "—"))
        self.lookup_row.addWidget(_metric_widget("Torque", f"{ltor:.2f} Nm" if ltor is not None else "—"))
        self.lookup_row.addWidget(_metric_widget(
            "Motor / ESC Temp",
            f"{lmt:.1f} / {let:.1f} °C" if (lmt is not None and let is not None) else "—"))
        self.lookup_row.addStretch()

    def _render_plot(self):
        df = self.df
        if "Time" not in df.columns:
            self._set_plot_placeholder()
            return
        if "Thrust" in df.columns:
            y_col, color, y_label, title = "Thrust", "#f97316", "N", "Thrust vs Time"
        elif "RPM" in df.columns:
            y_col, color, y_label, title = "RPM", "#3b82f6", "RPM", "RPM vs Time"
        else:
            self._set_plot_placeholder()
            return

        fig = pl_single(df, y_col, color, y_col, y_label, title)
        fig.update_layout(paper_bgcolor="#0d0f14", plot_bgcolor="#0d0f14")
        chart_html = fig.to_html(include_plotlyjs="cdn", full_html=False)
        html = f"""
        <html>
        <head><style>
            html, body {{ background:#0d0f14; margin:0; padding:0; }}
        </style></head>
        <body>{chart_html}</body>
        </html>
        """
        self.plot_view.setHtml(html)
