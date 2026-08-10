"""
results_tab.py — Results tab (PyQt6)

Port of view_dashboard.render_results(). Same max/abs-max computations
from the dataframe, same start/end-row battery voltage logic.
"""

import pandas as pd
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QScrollArea

_BLANK = {"", "None", "nan"}

FIELDS = [
    ("max_rpm", "Max. RPM"), ("max_thrust", "Max. Thrust (N)"), ("max_torque", "Max. Torque (Nm)"),
    ("max_esc_temp", "Max. ESC Temp (°C)"), ("max_motor_temp", "Max. Motor Temp (°C)"),
    ("max_esc_inlet_temp", "Max. ESC Inlet Temp (°C)"), ("max_motor_inlet_temp", "Max. Motor Inlet Temp (°C)"),
    ("max_esc_pressure", "Max. ESC Pressure (Bar)"),
    ("max_fin_inlet_temp", "Fin Inlet Temp (°C)"), ("max_fin_outlet_temp", "Fin Outlet Temp (°C)"),
    ("battery_voltage_start", "Battery Voltage (start V)"), ("battery_voltage_post", "Battery Voltage (end V)"),
    ("time_at_target_rpm", "Time at Target RPM (s)"),
]


def _maxcol(df, col):
    try:
        return float(df[col].max()) if col in df.columns and df[col].notna().any() else None
    except Exception:
        return None


def _absmaxcol(df, col):
    try:
        return float(df[col].abs().max()) if col in df.columns and df[col].notna().any() else None
    except Exception:
        return None


def _fmt(v, fmt):
    try:
        return fmt.format(float(v)) if v is not None else ""
    except Exception:
        return ""


class ResultsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.filename = None
        self.edits = {}

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        grid = QGridLayout(content)
        grid.setSpacing(10)

        for row, (key, label) in enumerate(FIELDS):
            grid.addWidget(QLabel(label), row, 0)
            edit = QLineEdit()
            edit.setMinimumWidth(220)
            grid.addWidget(edit, row, 1)
            self.edits[key] = edit

        self.caption = QLabel("Auto-filled from log data — edit if needed and click Update Parameters.")
        self.caption.setStyleSheet("color:#6b7280; font-size:11px;")
        outer.addWidget(self.caption)

    def load_run(self, df: pd.DataFrame, filename: str, saved_rp: dict):
        self.filename = filename

        rpm_ok = "RPM" in df.columns and df["RPM"].notna().any()
        time_at_rpm = None
        if rpm_ok:
            at_rpm = df[df["RPM"] >= 0.90 * df["RPM"].max()]
            if len(at_rpm) > 1:
                time_at_rpm = float(at_rpm["Time"].max() - at_rpm["Time"].min())

        start_row = df[df["RPM"] >= 50].iloc[0] if rpm_ok and (df["RPM"] >= 50).any() else df.iloc[0]
        end_mask = df["RPM"] >= 0.90 * df["RPM"].max() if rpm_ok else None
        end_row = df[end_mask].iloc[-1] if rpm_ok and end_mask.any() else df.iloc[-1]

        def rv(row, col):
            try:
                v = float(row[col])
                return v if pd.notna(v) else None
            except Exception:
                return None

        defaults = {
            "max_rpm": _fmt(_maxcol(df, "RPM"), "{:.0f}"),
            "max_thrust": _fmt(_maxcol(df, "Thrust"), "{:.2f}"),
            "max_torque": _fmt(_absmaxcol(df, "Torque"), "{:.2f}"),
            "max_esc_temp": _fmt(_maxcol(df, "ESC_Temp"), "{:.1f}"),
            "max_motor_temp": _fmt(_maxcol(df, "Motor_Temp"), "{:.1f}"),
            "max_esc_inlet_temp": _fmt(_maxcol(df, "ESC_Inlet_Temp_C"), "{:.1f}"),
            "max_motor_inlet_temp": _fmt(_maxcol(df, "Motor_Inlet_Temp_C"), "{:.1f}"),
            "max_esc_pressure": _fmt(_maxcol(df, "ESC_Pressure"), "{:.3f}"),
            "max_fin_inlet_temp": _fmt(_maxcol(df, "Fin_Inlet_Temp_C"), "{:.1f}"),
            "max_fin_outlet_temp": _fmt(_maxcol(df, "Fin_Outlet_Temp_C"), "{:.1f}"),
            "time_at_target_rpm": _fmt(time_at_rpm, "{:.1f}"),
            "battery_voltage_start": _fmt(rv(start_row, "Voltage"), "{:.2f}"),
            "battery_voltage_post": _fmt(rv(end_row, "Voltage"), "{:.2f}"),
        }

        merged = {}
        for k, default_val in defaults.items():
            saved_val = str(saved_rp.get(k, "")).strip()
            merged[k] = saved_val if saved_val and saved_val not in _BLANK else default_val

        for key, edit in self.edits.items():
            edit.setText(str(merged.get(key, "")))

    def get_values(self) -> dict:
        return {k: edit.text() for k, edit in self.edits.items()}
