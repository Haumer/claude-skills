"""APA7-styled matplotlib charts.

Usage:
    from apa7_chart import apa7_style, save_figure
    import matplotlib.pyplot as plt

    with apa7_style():
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.plot(years, values)
        ax.set_xlabel("Year")
        ax.set_ylabel("Revenue (USD millions)")
        save_figure(fig, "fig1.png",
                    caption="Annual revenue, 2018-2025.",
                    source="Internal finance dashboard, retrieved 2026-05-01.")
"""

import contextlib
from pathlib import Path

import matplotlib as mpl


APA7_RC = {
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif", "Liberation Serif", "Nimbus Roman"],
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.titleweight": "normal",
    "axes.labelsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "axes.prop_cycle": mpl.cycler(color=["#000000", "#555555", "#888888", "#bbbbbb"]),
    "lines.linewidth": 1.2,
    "lines.markersize": 4,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.dpi": 100,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "legend.frameon": False,
    "legend.fontsize": 9,
}


@contextlib.contextmanager
def apa7_style():
    """Context manager applying APA7 matplotlib defaults."""
    with mpl.rc_context(APA7_RC):
        yield


def save_figure(fig, path, caption: str, source: str) -> dict:
    """Save figure as 300 DPI PNG and emit a sidecar caption file.

    Writes:
      - <path>             the PNG
      - <path>.caption.txt the APA7-formatted caption ("Figure N. ...\\nNote. Source: ...")

    The caption file is meant to be pasted under the figure in your Typst document.

    Returns:
      dict with 'figure', 'caption', 'number'.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=300, bbox_inches="tight")
    fig_num = _next_figure_number(p.parent)
    caption_text = f"Figure {fig_num}. {caption.strip()}\nNote. Source: {source.strip()}"
    p.with_suffix(p.suffix + ".caption.txt").write_text(caption_text)
    return {"figure": str(p), "caption": caption_text, "number": fig_num}


def _next_figure_number(directory: Path) -> int:
    existing = list(directory.glob("*.caption.txt"))
    return len(existing) + 1
