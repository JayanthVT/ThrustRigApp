"""
test_check_tab.py — Test Parameter Check tab (PyQt6)

Port of view_dashboard.render_test_parameter_check(), using QTableWidget
instead of a manually-keyed loop. This sidesteps the whole delete-row bug
class from the Streamlit version: QTableWidget owns row identity itself
(removeRow(row) operates on the actual widget row, not a string key), so
there's no way for widget state to desync from the underlying list.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QCheckBox, QHeaderView, QLabel, QAbstractItemView, QMessageBox
)
from PyQt6.QtCore import Qt

from python_functions.db import update_test_param_check

_DEFAULT_TPC_ROWS = [
    "Coolant reservoir ~ 5 ltrs",
    "Flow rate ~ 8 LPM",
    "Pressure, flow rate, temperature values at ESC inlet",
    "Pressure, flow rate, temperature values at Motor inlet",
    "Temperature values at Fintube / Radiator inlet and Outlet",
    "Accelerometer at Motor Cover plate",
    "Pressure, flow rate, values at pump inlet",
    "Camera installed inside thrust rig",
    (
        "Increase in any of the following temperatures during the step test "
        "at any point.\n"
        "  a. ESC Inlet coolant temp. (45 °C)\n"
        "  b. ESC core temp. (45 °C)\n"
        "  c. Motor Inlet coolant temp. (50 °C)\n"
        "  d. Motor core temp. (100 °C)"
    ),
    "Current limit not exceeding 120 A for ESC",
    "Torque of bolts checked after run",
    "All joints are leakage free",
]

COL_CRITERIA, COL_PASS, COL_FAIL, COL_REMARKS, COL_DELETE = range(5)


class TestCheckTab(QWidget):
    def __init__(self, db_path=None):
        super().__init__()
        self.filename = None
        self.db_path = db_path

        root = QVBoxLayout(self)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Parameter / Criteria", "Pass", "Fail", "Remarks", ""]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_CRITERIA, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_REMARKS, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_PASS, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_FAIL, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_DELETE, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        root.addWidget(self.table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("➕ Add row")
        add_btn.clicked.connect(lambda: self._add_row("", False, False, ""))
        btn_row.addWidget(add_btn)

        save_btn = QPushButton("💾 Save Test Parameter Check")
        save_btn.clicked.connect(self.save)
        btn_row.addWidget(save_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color:#22c55e; font-size:11px;")
        root.addWidget(self.status_label)

    # ── Row management ──────────────────────────────────────
    def _add_row(self, criteria: str, passed: bool, failed: bool, remarks: str):
        r = self.table.rowCount()
        self.table.insertRow(r)

        self.table.setItem(r, COL_CRITERIA, QTableWidgetItem(criteria))
        self.table.setItem(r, COL_REMARKS, QTableWidgetItem(remarks))

        pass_cb = QCheckBox()
        pass_cb.setChecked(passed)
        pass_cb.stateChanged.connect(lambda _, row=None: self._on_pass_changed(pass_cb))
        pass_container = QWidget()
        pl = QHBoxLayout(pass_container)
        pl.addWidget(pass_cb)
        pl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pl.setContentsMargins(0, 0, 0, 0)
        self.table.setCellWidget(r, COL_PASS, pass_container)

        fail_cb = QCheckBox()
        fail_cb.setChecked(failed)
        fail_cb.stateChanged.connect(lambda _, row=None: self._on_fail_changed(fail_cb))
        fail_container = QWidget()
        fl = QHBoxLayout(fail_container)
        fl.addWidget(fail_cb)
        fl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fl.setContentsMargins(0, 0, 0, 0)
        self.table.setCellWidget(r, COL_FAIL, fail_container)

        del_btn = QPushButton("🗑")
        del_btn.setFixedWidth(36)
        # QTableWidget resolves the button's *current* row at click time via
        # indexAt(), not a captured index — so this stays correct even after
        # earlier rows are deleted and everything shifts up.
        del_btn.clicked.connect(lambda: self._delete_row(del_btn))
        self.table.setCellWidget(r, COL_DELETE, del_btn)

        self.table.setRowHeight(r, 56)

    def _delete_row(self, button: QPushButton):
        for row in range(self.table.rowCount()):
            if self.table.cellWidget(row, COL_DELETE) is button:
                self.table.removeRow(row)
                return

    def _on_pass_changed(self, pass_cb: QCheckBox):
        if pass_cb.isChecked():
            row = self._row_of_checkbox(pass_cb, COL_PASS)
            if row is not None:
                fail_container = self.table.cellWidget(row, COL_FAIL)
                fail_cb = fail_container.findChild(QCheckBox)
                fail_cb.setChecked(False)
                remarks_item = self.table.item(row, COL_REMARKS)
                if remarks_item and not remarks_item.text():
                    remarks_item.setText("OKAY")

    def _on_fail_changed(self, fail_cb: QCheckBox):
        if fail_cb.isChecked():
            row = self._row_of_checkbox(fail_cb, COL_FAIL)
            if row is not None:
                pass_container = self.table.cellWidget(row, COL_PASS)
                pass_cb = pass_container.findChild(QCheckBox)
                pass_cb.setChecked(False)
                remarks_item = self.table.item(row, COL_REMARKS)
                if remarks_item and remarks_item.text() == "OKAY":
                    remarks_item.setText("")

    def _row_of_checkbox(self, cb: QCheckBox, col: int):
        for row in range(self.table.rowCount()):
            container = self.table.cellWidget(row, col)
            if container and container.findChild(QCheckBox) is cb:
                return row
        return None

    # ── Public API ───────────────────────────────────────────
    def load_run(self, filename: str, saved_rows: list):
        self.filename = filename
        self.table.setRowCount(0)
        self.status_label.setText("")

        rows = saved_rows if saved_rows else [
            {"criteria": c, "passed": False, "failed": False, "remarks": ""}
            for c in _DEFAULT_TPC_ROWS
        ]
        for row in rows:
            self._add_row(
                row.get("criteria", ""), row.get("passed", False),
                row.get("failed", False), row.get("remarks", "")
            )

    def get_rows(self) -> list:
        rows = []
        for r in range(self.table.rowCount()):
            criteria_item = self.table.item(r, COL_CRITERIA)
            remarks_item = self.table.item(r, COL_REMARKS)
            pass_cb = self.table.cellWidget(r, COL_PASS).findChild(QCheckBox)
            fail_cb = self.table.cellWidget(r, COL_FAIL).findChild(QCheckBox)
            rows.append({
                "criteria": criteria_item.text() if criteria_item else "",
                "passed": pass_cb.isChecked(),
                "failed": fail_cb.isChecked(),
                "remarks": remarks_item.text() if remarks_item else "",
            })
        return rows

    def save(self):
        if not self.filename:
            return
        try:
            update_test_param_check(self.filename, self.get_rows(), db_path=self.db_path)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", f"Could not save:\n\n{e}")
            return
        self.status_label.setText("✅ Test Parameter Check saved.")
