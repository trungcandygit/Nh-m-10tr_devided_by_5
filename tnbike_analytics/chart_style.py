"""
Chart style helper — lấy từ Python Graph Gallery
https://github.com/holtzy/The-Python-Graph-Gallery
"""
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.lines as mlines

# ── Màu nền & lưới (từ gallery notebooks) ──────────────────────────────────
BG_WHITE  = "#fafaf5"     # nền figure (web-lollipop, web-line notebooks)
BG_AXES   = "#f8f8f8"     # nền axes
GREY91    = "#e8e8e8"     # đường grid nhạt
GREY82    = "#d1d1d1"     # đường tham chiếu
GREY70    = "#B3B3B3"     # phụ
GREY40    = "#666666"     # nhãn phụ
BLUE_ECO  = "#076fa2"     # Economist blue
RED_ECO   = "#E3120B"     # Economist red

# ── Gallery primary palette ─────────────────────────────────────────────────
PALETTE = ["#69b3a2", "#404080", "#e85252", "#f4a261", "#2a9d8f",
           "#264653", "#e9c46a", "#e76f51"]

# ── Màu thương hiệu tnbike ──────────────────────────────────────────────────
BRAND = {
    "CITYBIKE_P":  "#1D9E75",
    "KIDBIKE_1":   "#378ADD",
    "KIDBIKE_2":   "#7F77DD",
    "SPORTBIKE_S": "#D85A30",
    "SPORTBIKE_A": "#BA7517",
}
BRAND_LABELS = {
    "CITYBIKE_P":  "Xe phổ thông",
    "KIDBIKE_1":   "Xe trẻ em N1",
    "KIDBIKE_2":   "Xe trẻ em N2",
    "SPORTBIKE_S": "Thể thao thép",
    "SPORTBIKE_A": "Thể thao nhôm",
}
GROUP_ORDER = ["CITYBIKE_P", "KIDBIKE_1", "KIDBIKE_2", "SPORTBIKE_S", "SPORTBIKE_A"]

REGION_COLORS = {
    "Miền Bắc": "#378ADD",
    "Miền Trung": "#f4a261",
    "Miền Nam":  "#1D9E75",
}


# ── Core style function ──────────────────────────────────────────────────────

def apply_gallery_style(ax,
                        title="",
                        subtitle="",
                        xlabel="",
                        ylabel="",
                        grid_axis="y",
                        remove_spines=("top", "right"),
                        bg=BG_AXES):
    """
    Áp dụng style Python Graph Gallery cho một axes.
    Dùng sau khi vẽ chart, trước khi save.
    """
    # Background
    ax.set_facecolor(bg)
    ax.figure.patch.set_facecolor(BG_WHITE)

    # Grid
    if grid_axis:
        ax.set_axisbelow(True)
        ax.grid(axis=grid_axis, color="white", linewidth=1.5, alpha=0.9)

    # Spines
    for sp in remove_spines:
        ax.spines[sp].set_visible(False)
    for sp in set(["top","right","left","bottom"]) - set(remove_spines):
        ax.spines[sp].set_color(GREY82)
        ax.spines[sp].set_linewidth(1.2)

    # Ticks
    ax.tick_params(length=0, labelsize=10, labelcolor=GREY40)

    # Labels
    if title:
        ax.set_title(title, fontsize=14, fontweight="bold", loc="left",
                     pad=12, color="#202020")
    if subtitle:
        ax.annotate(subtitle, xy=(0, 1.02), xycoords="axes fraction",
                    fontsize=10, color=GREY40, ha="left")
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=11, labelpad=8, color=GREY40)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=11, labelpad=8, color=GREY40)

    return ax


def add_watermark(ax, text="Xe đạp Thống Nhất  •  DATA EXPLORERS 2026"):
    """Dòng nguồn ở góc dưới phải."""
    ax.annotate(text,
                xy=(1, -0.08), xycoords="axes fraction",
                ha="right", va="top",
                fontsize=8, color=GREY70, style="italic")


def add_top_bar(fig, color=RED_ECO, height=0.018):
    """Thanh màu trên cùng figure — phong cách Economist."""
    import matplotlib.patches as mpatches
    fig.add_artist(mpatches.Rectangle(
        (0, 1 - height), 1, height,
        transform=fig.transFigure,
        color=color, zorder=10, clip_on=False
    ))


def legend_patches(groups=None):
    """Tạo legend handles cho các nhóm SP tnbike."""
    if groups is None:
        groups = GROUP_ORDER
    return [mpatches.Patch(color=BRAND[g], label=BRAND_LABELS[g])
            for g in groups if g in BRAND]
