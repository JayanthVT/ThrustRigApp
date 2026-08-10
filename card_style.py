"""
card_style.py — shared metric-card widget.

Both dashboard_tab.py and measurable_tab.py used to build their own
metric card (slightly differently, which is why they looked inconsistent
across tabs). Centralised here so every metric card in the app matches.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel


def metric_card(label: str, value: str, sub: str = "", tooltip: str = "") -> QFrame:
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

    lbl = QLabel(label.upper())
    lbl.setStyleSheet(
        "color:#8b93a7; font-size:11px; font-weight:600; "
        "letter-spacing:1px; background:transparent; border:none;"
    )
    v.addWidget(lbl)

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
