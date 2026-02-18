"""Central plotting style."""

from matplotlib import pyplot as plt

PALETTE = {
    "bg": "#f3f0e8",
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
            "font.size": 11,
        }
    )
