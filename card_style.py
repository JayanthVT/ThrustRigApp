"""
card_style.py — shared metric-card widget.

Both dashboard_tab.py and measurable_tab.py used to build their own
metric card (slightly differently, which is why they looked inconsistent
across tabs). Centralised here so every metric card in the app matches.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel


def metric_card(label: str, value: str, sub: str = "", tooltip: str = "", formula: str = "") -> QFrame:
    """
    tooltip: hover text on the whole card (e.g. Dashboard's "Timestamp: ...").
    formula: shows a small visible "?" badge next to the label — for
    Measurable Params, where you actually want people to notice there's
    an explanation available, not just stumble onto an invisible
    whole-card tooltip. Distinct from `tooltip` so both can be used
    independently without one overwriting the other.
    """
    box = QFrame()
    box.setObjectName("metricCard")
    box.setMinimumWidth(160)
    box.setStyleSheet("""
        #metricCard {
            background: #161a24;
            border: 1px solid #2b3040;
            border-radius: 10px;
        }
    """)
    v = QVBoxLayout(box)
    v.setContentsMargins(16, 14, 16, 14)
    v.setSpacing(4)

    header_row = QHBoxLayout()
    header_row.setSpacing(6)
    lbl = QLabel(label.upper())
    lbl.setStyleSheet(
        "color:#8b93a7; font-size:11px; font-weight:600; "
        "letter-spacing:1px; background:transparent; border:none;"
    )
    header_row.addWidget(lbl)
    header_row.addStretch()

    if formula:
        badge = QLabel("?")
        badge.setFixedSize(15, 15)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet("""
            background: #2b3040;
            color: #b8c0d4;
            border-radius: 7px;
            font-size: 10px;
            font-weight: 700;
        """)
        badge.setToolTip(formula)
        badge.setCursor(Qt.CursorShape.WhatsThisCursor)
        header_row.addWidget(badge)

    v.addLayout(header_row)

    val = QLabel(value)
    val.setStyleSheet(
        "color:#f2f2f2; font-size:24px; font-weight:700; "
        "background:transparent; border:none;"
    )
    v.addWidget(val)

    if sub:
        subl = QLabel(sub)
        subl.setStyleSheet(
            "color:#6b7280; font-size:11px; background:transparent; border:none; margin-top:2px;"
        )
        v.addWidget(subl)

    if tooltip:
        box.setToolTip(tooltip)
    return box
