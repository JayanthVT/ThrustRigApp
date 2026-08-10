"""
initial_params_tab.py — Initial Parameters tab (PyQt6)

Port of view_dashboard.render_initial_parameters(). Same default-computation
and saved-value-merge logic; QLineEdit/QTextEdit instead of st.text_input.
"""

import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QTextEdit, QScrollArea
)

from python_functions.data_pipeline import default_init_params

_BLANK = {"", "0", "0.0", "0.00", "0.000", "-", "-%", "None"}

FIELDS = [
    # (key, label)
    ("res_capacity", "Capacity (L)"), ("res_composition", "Composition"),
    ("res_temperature", "Reservoir Temperature (°C)"),
    ("duty_cycle", "Duty cycle & flowrate"),
    ("init_esc_temp", "Initial ESC Temp (°C)"), ("init_motor_temp", "Initial Motor Temp (°C)"),
    ("ambient_temp", "Ambient (°C)"), ("esc_inlet_coolant", "ESC Inlet Coolant (°C)"),
    ("motor_inlet_coolant", "Motor Inlet Coolant (°C)"),
    ("esc_inlet_flow", "ESC Inlet Flow (LPM)"), ("motor_inlet_flow", "Motor Inlet Flow (LPM)"),
    ("esc_inlet_pressure", "ESC Inlet Pressure (Bar)"), ("motor_inlet_pressure", "Motor Inlet Pressure (Bar)"),
    ("battery_voltage", "Battery Voltage (V)"), ("battery_soc", "Battery SOC"), ("battery_soh", "Battery SOH"),
    ("fin_inlet_temp", "Fintube Inlet Temp (°C)"), ("fin_outlet_temp", "Fintube Outlet Temp (°C)"),
]


class InitialParametersTab(QWidget):
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

        row = 0
        for key, label in FIELDS:
            grid.addWidget(QLabel(label), row, 0)
            edit = QLineEdit()
            edit.setMinimumWidth(220)
            grid.addWidget(edit, row, 1)
            self.edits[key] = edit
            row += 1

        grid.addWidget(QLabel("Notes"), row, 0)
        self.notes_edit = QTextEdit()
        self.notes_edit.setFixedHeight(80)
        grid.addWidget(self.notes_edit, row, 1)

        self.caption = QLabel("")
        self.caption.setStyleSheet("color:#6b7280; font-size:11px;")
        outer.addWidget(self.caption)

    def load_run(self, df: pd.DataFrame, filename: str, saved_ip: dict):
        self.filename = filename
        defaults = default_init_params(df)

        merged = {}
        for k, default_val in defaults.items():
            saved_val = str(saved_ip.get(k, "")).strip()
            merged[k] = saved_val if saved_val and saved_val not in _BLANK else default_val
        for k in ("res_capacity", "res_composition", "duty_cycle", "battery_soc", "battery_soh",
                  "ambient_temp", "notes", "motor_inlet_flow", "motor_inlet_pressure"):
            if k in saved_ip and str(saved_ip[k]).strip():
                merged[k] = saved_ip[k]

        for key, edit in self.edits.items():
            edit.setText(str(merged.get(key, "")))
        self.notes_edit.setPlainText(str(merged.get("notes", "")))

        self.caption.setText(
            "✅ Loaded from library — edit and click Update Parameters to save."
            if saved_ip else "Auto-filled from first log row — edit as needed."
        )

    def get_values(self) -> dict:
        vals = {k: edit.text() for k, edit in self.edits.items()}
        vals["notes"] = self.notes_edit.toPlainText()
        return vals
