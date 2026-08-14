"""
charts.py — Chart helpers for Thrust Test Rig Dashboard
Plotly helpers for interactive screen charts.
Matplotlib helpers for PDF-quality static charts.
No Streamlit imports.
"""

import io
import matplotlib.pyplot as plt

# ─────────────────────────────────────────────
# MATPLOTLIB DARK STYLE
# ─────────────────────────────────────────────
DARK = {
    "figure.facecolor": "#0d0f14",
    "axes.facecolor":   "#13161e",
    "axes.edgecolor":   "#2a2d3a",
    "axes.labelcolor":  "#c8ccd8",
    "axes.grid":        True,
    "grid.color":       "#1e2130",
    "grid.linestyle":   "--",
    "grid.linewidth":   0.5,
    "xtick.color":      "#6b7280",
    "ytick.color":      "#6b7280",
    "text.color":       "#c8ccd8",
    "legend.facecolor": "#13161e",
    "legend.edgecolor": "#2a2d3a",
}

# ─────────────────────────────────────────────
# PLOTLY STYLE CONSTANTS
# ─────────────────────────────────────────────
_PL_BG     = "#0d0f14"
_PL_PAPER  = "#13161e"
_PL_GRID   = "#1e2130"
_PL_TEXT   = "#c8ccd8"
_PL_TICK   = "#6b7280"
_PL_BORDER = "#2a2d3a"


def _pl_base_layout(title="", height=380):
    return dict(
        title=dict(text=title, font=dict(color=_PL_TEXT, size=12), x=0.01),
        plot_bgcolor=_PL_BG, paper_bgcolor=_PL_PAPER,
        font=dict(color=_PL_TEXT, family="monospace", size=11),
        legend=dict(bgcolor=_PL_PAPER, bordercolor=_PL_BORDER, borderwidth=1,
                    font=dict(color=_PL_TEXT)),
        margin=dict(l=60, r=60, t=45, b=45),
        hovermode="x unified",
        height=height,
    )


def _pl_xaxis(label="Time (s)"):
    return dict(
        title=dict(text=label, font=dict(color=_PL_TICK)),
        gridcolor=_PL_GRID, gridwidth=0.5,
        showline=True, linecolor=_PL_BORDER,
        tickfont=dict(color=_PL_TICK)
    )


def _pl_yaxis(label, color):
    return dict(
        title=dict(text=label, font=dict(color=color)),
        tickfont=dict(color=color),
        gridcolor=_PL_GRID, gridwidth=0.5,
        showline=True, linecolor=_PL_BORDER
    )


# ─────────────────────────────────────────────
# PLOTLY CHART FUNCTIONS
# All accept optional df2 for compare mode overlay.
# ─────────────────────────────────────────────

def pl_single(df, y_col, color, ylabel, unit, title,
              df2=None, label1="Run A", label2="Run B"):
    """Single Y axis Plotly chart. Optionally overlay df2 for comparison."""
    import plotly.graph_objects as _go
    fig   = _go.Figure()
    _step = max(1, len(df) // 5000)
    _df   = df.iloc[::_step]

    fig.add_trace(_go.Scatter(
        x=_df["Time"], y=_df[y_col], mode="lines",
        name=f"{y_col} ({label1})",
        line=dict(color=color, width=1.6),
        hovertemplate=f"<b>Time</b>: %{{x:.2f}}s<br>"
                      f"<b>{y_col}</b>: %{{y:.3f}} {unit}<extra>{label1}</extra>",
    ))
    if df2 is not None and y_col in df2.columns and "Time" in df2.columns:
        _step2 = max(1, len(df2) // 5000)
        _df2   = df2.iloc[::_step2]
        fig.add_trace(_go.Scatter(
            x=_df2["Time"], y=_df2[y_col], mode="lines",
            name=f"{y_col} ({label2})",
            line=dict(color="#38bdf8", width=1.4, dash="dash"),
            hovertemplate=f"<b>Time</b>: %{{x:.2f}}s<br>"
                          f"<b>{y_col}</b>: %{{y:.3f}} {unit}<extra>{label2}</extra>",
        ))
    layout = _pl_base_layout(title)
    layout["xaxis"] = _pl_xaxis()
    layout["yaxis"] = _pl_yaxis(f"{ylabel} ({unit})", color)
    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────
# MATPLOTLIB CHART FUNCTIONS (PDF only)
# ─────────────────────────────────────────────

def fig_to_png(fig, dpi=150) -> bytes:
    """Convert a matplotlib figure to PNG bytes and close it."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()
