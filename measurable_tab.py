"""
measurable_tab.py — Measurable Parameters & Efficiency tab (PyQt6)

Port of view_dashboard.render_measurable_parameters(). Same steady-state
auto-detection (rolling RPM std-dev window search) and the same
torque/thrust -> mechanical/electrical power -> efficiency calculation.
Session-only, same as the Streamlit version (not persisted to DB).
"""

import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QDoubleSpinBox,
    QPushButton, QFrame, QScrollArea
)


from card_style import metric_card


def _metric(label, value, sub=""):
    return metric_card(label, value, sub=sub)


class MeasurableParametersTab(QWidget):
    def __init__(self):
        super().__init__()
        self.df: pd.DataFrame | None = None
        self.last_results = None

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        root = QVBoxLayout(content)
        root.setSpacing(14)

        root.addWidget(QLabel("Steady-state window"))
        cap = QLabel("Auto-detected from lowest RPM variance — verify and edit if needed.")
        cap.setStyleSheet("color:#6b7280; font-size:11px;")
        root.addWidget(cap)

        win_row = QHBoxLayout()
        win_row.addWidget(QLabel("Window start (s)"))
        self.win_start = QDoubleSpinBox()
        self.win_start.setRange(0, 999999)
        self.win_start.setDecimals(1)
        win_row.addWidget(self.win_start)
        win_row.addSpacing(20)
        win_row.addWidget(QLabel("Window end (s)"))
        self.win_end = QDoubleSpinBox()
        self.win_end.setRange(0, 999999)
        self.win_end.setDecimals(1)
        win_row.addWidget(self.win_end)
        win_row.addStretch()
        root.addLayout(win_row)

        root.addWidget(QLabel("Manual inputs"))
        inp_row = QHBoxLayout()
        inp_row.addWidget(QLabel("Torque (Nm) — load cell"))
        self.inp_torque = QDoubleSpinBox()
        self.inp_torque.setRange(-999999, 999999)
        self.inp_torque.setDecimals(2)
        self.inp_torque.setSingleStep(0.5)
        inp_row.addWidget(self.inp_torque)
        inp_row.addSpacing(20)
        inp_row.addWidget(QLabel("Thrust (N) — load cell"))
        self.inp_thrust = QDoubleSpinBox()
        self.inp_thrust.setRange(-999999, 999999)
        self.inp_thrust.setDecimals(2)
        self.inp_thrust.setSingleStep(1.0)
        inp_row.addWidget(self.inp_thrust)
        inp_row.addStretch()
        root.addLayout(inp_row)

        self.log_mean_caption = QLabel("")
        self.log_mean_caption.setStyleSheet("color:#6b7280; font-size:11px;")
        root.addWidget(self.log_mean_caption)

        calc_btn = QPushButton("⚙️ Calculate")
        calc_btn.clicked.connect(self.calculate)
        root.addWidget(calc_btn)

        self.results_caption = QLabel("")
        self.results_caption.setStyleSheet("color:#6b7280; font-size:11px;")
        root.addWidget(self.results_caption)

        self.mech_row = QHBoxLayout()
        root.addWidget(QLabel("🔧 Mechanical"))
        root.addLayout(self.mech_row)

        self.elec_row = QHBoxLayout()
        root.addWidget(QLabel("⚡ Electrical"))
        root.addLayout(self.elec_row)

        self.eff_row = QHBoxLayout()
        root.addWidget(QLabel("📊 Efficiency"))
        root.addLayout(self.eff_row)

        root.addStretch()

    def load_run(self, df: pd.DataFrame):
        self.df = df
        self.last_results = None
        self._clear_layout(self.mech_row)
        self._clear_layout(self.elec_row)
        self._clear_layout(self.eff_row)
        self.results_caption.setText("")

        auto_s, auto_e = 0.0, float(df["Time"].max())
        has_rpm = "RPM" in df.columns and df["RPM"].notna().any()
        if has_rpm and len(df) > 50:
            gm = df[df["RPM"] > 0]["RPM"].mean()
            thr = 0.01 * gm
            dt = df["Time"].diff().median()
            wr = max(int(5.0 / dt), 10) if dt > 0 else 50
            rs = df["RPM"].rolling(wr, center=True).std().fillna(9999)
            sm = rs < thr
            best_len = best_start = cur_len = cur_start = 0
            for i, st in enumerate(sm):
                if st:
                    if cur_len == 0:
                        cur_start = i
                    cur_len += 1
                    if cur_len > best_len:
                        best_len, best_start = cur_len, cur_start
                else:
                    cur_len = 0
            if best_len > 10:
                auto_s = float(df["Time"].iloc[best_start])
                auto_e = float(df["Time"].iloc[min(best_start + best_len - 1, len(df) - 1)])

        self.win_start.setMaximum(float(df["Time"].max()))
        self.win_end.setMaximum(float(df["Time"].max()))
        self.win_start.setValue(round(auto_s, 1))
        self.win_end.setValue(round(auto_e, 1))

        dfw_preview = df[(df["Time"] >= auto_s) & (df["Time"] <= auto_e)]
        has_torque = "Torque" in df.columns and (df["Torque"].abs() > 0).any()
        has_thrust = "Thrust" in df.columns and (df["Thrust"].abs() > 0).any()
        torque_default = float(dfw_preview["Torque"].abs().mean()) if has_torque and len(dfw_preview) else 0.0
        thrust_default = float(dfw_preview["Thrust"].abs().mean()) if has_thrust and len(dfw_preview) else 0.0
        self.inp_torque.setValue(torque_default)
        self.inp_thrust.setValue(thrust_default)
        self.log_mean_caption.setText(
            f"Log mean — Torque: {torque_default:.2f} Nm  |  Thrust: {thrust_default:.2f} N"
        )

    def calculate(self):
        df = self.df
        if df is None:
            return
        win_start, win_end = self.win_start.value(), self.win_end.value()
        dfw = df[(df["Time"] >= win_start) & (df["Time"] <= win_end)].copy()
        if len(dfw) < 5:
            self.results_caption.setText("⚠️ Window too short — fewer than 5 rows.")
            return

        has_dc_volt = "Voltage" in df.columns
        has_curr = "Current" in df.columns
        inp_torque, inp_thrust = self.inp_torque.value(), self.inp_thrust.value()

        dfw["omega"] = dfw["RPM"] * (2 * np.pi / 60)
        dfw["P_mech"] = inp_torque * dfw["omega"]
        dfw["V_DC"] = dfw["Voltage"] if has_dc_volt else np.nan
        dfw["I_DC"] = dfw["Current"] if has_curr else np.nan
        dfw["P_DC"] = dfw["V_DC"] * dfw["I_DC"]
        dfw["T_g"] = inp_thrust * 101.972
        dfw["eta_overall"] = np.where(dfw["P_DC"] > 0, dfw["T_g"] / dfw["P_DC"], np.nan)
        dfw["eta_mech"] = np.where(dfw["P_DC"] > 0, (dfw["P_mech"] / dfw["P_DC"]) * 100, np.nan)

        def s(series):
            ser = pd.to_numeric(series, errors="coerce").dropna()
            return (float(ser.mean()), float(ser.std())) if len(ser) else (None, None)

        res = {
            "omega": s(dfw["omega"]), "P_mech": s(dfw["P_mech"]),
            "V_DC": s(dfw["V_DC"]), "I_DC": s(dfw["I_DC"]), "P_DC": s(dfw["P_DC"]),
            "eta_overall": s(dfw["eta_overall"]), "eta_mech": s(dfw["eta_mech"]),
        }
        self.last_results = res

        self.results_caption.setText(
            f"Results for window {win_start:.1f}s → {win_end:.1f}s  ({len(dfw):,} rows)  |  "
            f"Torque: {inp_torque:.2f} Nm  |  Thrust: {inp_thrust:.2f} N"
        )

        def met(key, unit, fmt):
            mv, sv = res.get(key, (None, None))
            if mv is None:
                return _metric(key, "—")
            return _metric(key.replace("_", " "), f"{mv:{fmt}} {unit}", f"±{sv:{fmt}} σ")

        self._clear_layout(self.mech_row)
        self.mech_row.addWidget(_metric("Shaft Torque (input)", f"{inp_torque:.2f} Nm"))
        self.mech_row.addWidget(met("omega", "rad/s", ".2f"))
        self.mech_row.addWidget(met("P_mech", "W", ".0f"))
        self.mech_row.addStretch()

        self._clear_layout(self.elec_row)
        self.elec_row.addWidget(met("V_DC", "V", ".2f"))
        self.elec_row.addWidget(met("I_DC", "A", ".2f"))
        self.elec_row.addWidget(met("P_DC", "W", ".0f"))
        self.elec_row.addStretch()

        self._clear_layout(self.eff_row)
        self.eff_row.addWidget(met("eta_overall", "g/W", ".4f"))
        self.eff_row.addWidget(met("eta_mech", "%", ".2f"))
        self.eff_row.addStretch()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
