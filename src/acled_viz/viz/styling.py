"""Central plotting style."""

from matplotlib import pyplot as plt

PALETTE = {
    "bg": "#f1ede3",
    "fg": "#1d2d44",
    "accent": "#a44a3f",
    "muted": "#6c7a89",
}


def apply_style() -> None:
    plt.style.use("default")
    plt.rcParams.update(
        {
            "figure.facecolor": PALETTE["bg"],
            "axes.facecolor": "#fcfbf8",
            "axes.edgecolor": PALETTE["fg"],
            "text.color": PALETTE["fg"],
            "axes.labelcolor": PALETTE["fg"],
            "xtick.color": PALETTE["fg"],
            "ytick.color": PALETTE["fg"],
            "grid.color": "#d8d0bf",
            "grid.linewidth": 0.8,
            "axes.titleweight": "semibold",
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Avenir Next",
                "Helvetica Neue",
                "Segoe UI",
                "DejaVu Sans",
            ],
            "font.size": 11,
        }
    )
