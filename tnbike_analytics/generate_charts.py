"""
Tạo 15 biểu đồ phân tích + dự báo — Xe đạp Thống Nhất
Style: Python Graph Gallery (https://github.com/holtzy/The-Python-Graph-Gallery)
Chạy: python generate_charts.py  (không cần PostgreSQL)
"""
import warnings
warnings.filterwarnings("ignore")
import logging
logging.disable(logging.CRITICAL)

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import seaborn as sns
from pathlib import Path

from analytics.sql_data_loader import load_all, build_fact
from chart_style import (
    apply_gallery_style, add_watermark, add_top_bar, legend_patches,
    BRAND, BRAND_LABELS, GROUP_ORDER, REGION_COLORS,
    BG_WHITE, BG_AXES, GREY40, GREY70, GREY82, GREY91,
    BLUE_ECO, RED_ECO, PALETTE
)

# ── Thư mục output ───────────────────────────────────────────────────────────
CHART_DIR = Path("output/charts")
TABLE_DIR  = Path("output/tables")
CHART_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)


def _save(fig, name, dpi=300):
    p = CHART_DIR / name
    fig.savefig(p, dpi=dpi, bbox_inches="tight", facecolor=BG_WHITE)
    plt.close(fig)
    print(f"  ✓ {p}")


# ── Tải dữ liệu ─────────────────────────────────────────────────────────────
print("⏳  Đang tải dữ liệu từ SQL...")
dfs  = load_all()
fact = build_fact(dfs)
print(f"    → {len(fact):,} dòng bán hàng | "
      f"{fact['so_number'].nunique():,} đơn hàng | "
      f"{fact['customer_code'].nunique():,} đại lý\n")

# ════════════════════════════════════════════════════════════════════════════
# CHART 01 — Xu hướng doanh thu theo tháng × nhóm SP
# Ref: web-line-chart-with-labels-at-line-end.ipynb
# ════════════════════════════════════════════════════════════════════════════
print("📊  Chart 01 — Xu hướng doanh thu theo tháng...")

monthly = (fact.groupby(["fiscal_year", "fiscal_month", "group_code"])["line_total"]
           .sum().reset_index())
monthly["ym_n"] = (monthly["fiscal_year"] - 2025) * 12 + monthly["fiscal_month"]
monthly["ym_label"] = monthly.apply(
    lambda r: f"T{int(r.fiscal_month)}/{str(int(r.fiscal_year))[2:]}", axis=1)

pivot = monthly.pivot_table(index=["ym_n","ym_label"], columns="group_code",
                             values="line_total", fill_value=0).reset_index()
pivot = pivot.sort_values("ym_n")
xticks = pivot["ym_n"].tolist()
xlabels = pivot["ym_label"].tolist()

fig, ax = plt.subplots(figsize=(14, 7))

for grp in GROUP_ORDER:
    if grp not in pivot.columns:
        continue
    y = pivot[grp].values / 1e9
    ax.plot(xticks, y, color=BRAND[grp], lw=2.5, marker="o",
            markersize=5, markerfacecolor="white", markeredgewidth=1.8, zorder=3)
    # Nhãn cuối dòng
    ax.text(xticks[-1] + 0.15, y[-1], BRAND_LABELS[grp],
            color=BRAND[grp], fontsize=9, fontweight="bold", va="center")

ax.set_xlim(xticks[0] - 0.3, xticks[-1] + 2.5)
ax.set_xticks(xticks)
ax.set_xticklabels(xlabels, rotation=0, fontsize=9)
apply_gallery_style(ax,
    title="Doanh thu theo tháng — từng nhóm sản phẩm",
    subtitle="T1/2025 – T2/2026  •  đơn vị: tỷ đồng",
    ylabel="Tỷ đồng")
add_watermark(ax)
add_top_bar(fig, color=BRAND["CITYBIKE_P"])
_save(fig, "01_doanh_thu_theo_thang.png")


# ════════════════════════════════════════════════════════════════════════════
# CHART 02 — Cơ cấu nhóm sản phẩm (Donut + Bar)
# Ref: 161-custom-matplotlib-donut-plot.ipynb + 1-basic-barplot.ipynb
# ════════════════════════════════════════════════════════════════════════════
print("📊  Chart 02 — Cơ cấu nhóm sản phẩm...")

rev_grp = fact.groupby("group_code")["line_total"].sum().reindex(GROUP_ORDER).fillna(0)
total_rev = rev_grp.sum()

fig, (ax_d, ax_b) = plt.subplots(1, 2, figsize=(14, 6))
fig.patch.set_facecolor(BG_WHITE)

# Donut
colors_d = [BRAND[g] for g in GROUP_ORDER]
wedges, _ = ax_d.pie(rev_grp.values, colors=colors_d,
                      startangle=90,
                      wedgeprops={"linewidth": 3, "edgecolor": BG_WHITE, "width": 0.55})
ax_d.add_artist(plt.Circle((0, 0), 0.45, color=BG_WHITE))
ax_d.text(0, 0, f"{total_rev/1e9:.1f}\ntỷ đồng", ha="center", va="center",
          fontsize=13, fontweight="bold", color="#202020")
ax_d.set_title("Cơ cấu doanh thu\ntheo nhóm sản phẩm",
               fontsize=13, fontweight="bold", loc="center", pad=10)

# Bar ngang
share_pct = (rev_grp / total_rev * 100).values
labels_b  = [BRAND_LABELS[g] for g in GROUP_ORDER]
y_pos = range(len(GROUP_ORDER))
bars = ax_b.barh(y_pos, rev_grp.values / 1e9, color=colors_d,
                  height=0.6, edgecolor=BG_WHITE, linewidth=2)
for bar, pct, rev in zip(bars, share_pct, rev_grp.values):
    ax_b.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
              f"{pct:.1f}%  ({rev/1e9:.1f} tỷ)",
              va="center", fontsize=10, color=GREY40)
ax_b.set_yticks(y_pos)
ax_b.set_yticklabels(labels_b, fontsize=10)
ax_b.invert_yaxis()
apply_gallery_style(ax_b,
    title="Doanh thu từng nhóm (tỷ đồng)",
    xlabel="Tỷ đồng",
    remove_spines=("top", "right", "bottom"),
    grid_axis="x")
ax_b.set_xlim(0, rev_grp.max() / 1e9 * 1.45)
add_watermark(ax_b)
add_top_bar(fig, color=BRAND["KIDBIKE_1"])
_save(fig, "02_co_cau_nhom_sp.png")


# ════════════════════════════════════════════════════════════════════════════
# CHART 03 — BCG Matrix
# Ref: web-bubble-plot-with-annotations-and-custom-features.ipynb
# ════════════════════════════════════════════════════════════════════════════
print("📊  Chart 03 — BCG Matrix...")

rev_2025    = fact[fact.fiscal_year == 2025].groupby("group_code")["line_total"].sum()
rev_q1_2026 = fact[(fact.fiscal_year == 2026) & (fact.fiscal_quarter == 1)].groupby("group_code")["line_total"].sum()
rev_q1_2025 = fact[(fact.fiscal_year == 2025) & (fact.fiscal_quarter == 1)].groupby("group_code")["line_total"].sum()
bcg = pd.DataFrame({"rev_2025": rev_2025, "rev_q1_26": rev_q1_2026,
                    "rev_q1_25": rev_q1_2025}).fillna(0)
bcg["market_share"] = bcg["rev_2025"] / bcg["rev_2025"].sum() * 100
bcg["growth"]       = ((bcg["rev_q1_26"] - bcg["rev_q1_25"])
                        / bcg["rev_q1_25"].replace(0, 1)) * 100

med_s = bcg["market_share"].median()
med_g = bcg["growth"].median()

BCG_LABELS = {
    (True, True):   ("Stars", "#BA7517"),
    (True, False):  ("Cash Cows", "#1D9E75"),
    (False, True):  ("Question Marks", "#378ADD"),
    (False, False): ("Dogs", "#888780"),
}

fig, ax = plt.subplots(figsize=(11, 7))
fig.patch.set_facecolor(BG_WHITE)
ax.set_facecolor(BG_AXES)
ax.set_axisbelow(True)
ax.grid(color="white", linewidth=1.5, alpha=0.9)

# Vùng nền 4 ô
xlim = (bcg["market_share"].min() - 3, bcg["market_share"].max() + 6)
ylim = (bcg["growth"].min() - 8, bcg["growth"].max() + 12)
ax.axvline(med_s, color=GREY82, lw=1.5, ls="--", zorder=1)
ax.axhline(med_g, color=GREY82, lw=1.5, ls="--", zorder=1)

# Nhãn 4 góc
for (hs, hg), (lbl, col) in BCG_LABELS.items():
    x = xlim[1] - 1 if hs else xlim[0] + 0.5
    y = ylim[1] - 2 if hg else ylim[0] + 1
    ax.text(x, y, lbl, fontsize=10, color=col, fontweight="bold",
            alpha=0.5, ha="right" if hs else "left")

for gc in GROUP_ORDER:
    if gc not in bcg.index:
        continue
    r = bcg.loc[gc]
    color = BCG_LABELS[(r.market_share >= med_s, r.growth >= med_g)][1]
    sz = max(300, r.rev_2025 / 1e9 * 35)
    ax.scatter(r.market_share, r.growth, s=sz, color=color, alpha=0.85,
               edgecolors="white", linewidths=2, zorder=5)
    ax.annotate(BRAND_LABELS[gc],
                xy=(r.market_share, r.growth),
                xytext=(10, 8), textcoords="offset points",
                fontsize=11, fontweight="bold", color=color,
                arrowprops=dict(arrowstyle="-", color=GREY82, lw=0.8))

ax.set_xlim(xlim); ax.set_ylim(ylim)
apply_gallery_style(ax,
    title="Ma trận BCG — Phân loại 5 nhóm sản phẩm",
    subtitle="Kích thước bong bóng ~ Doanh thu 2025  |  Trục X: Thị phần  |  Trục Y: Tăng trưởng Q1 YoY",
    xlabel="Thị phần doanh thu (%)",
    ylabel="Tăng trưởng Q1/2026 vs Q1/2025 (%)",
    remove_spines=("top", "right", "left", "bottom"), grid_axis=None)
add_watermark(ax)
add_top_bar(fig, color=BRAND["SPORTBIKE_A"])
_save(fig, "03_bcg_matrix.png")


# ════════════════════════════════════════════════════════════════════════════
# CHART 04 — RFM Scatter Bubble
# Ref: web-bubble-plot-with-annotations-and-custom-features.ipynb
# ════════════════════════════════════════════════════════════════════════════
print("📊  Chart 04 — RFM Scatter Bubble...")

ref_date = fact["order_date"].max() + pd.Timedelta(days=1)
rfm = fact.groupby(["customer_code", "customer_name"]).agg(
    last_order=("order_date", "max"),
    freq=("so_number", "nunique"),
    monetary=("line_total", "sum")
).reset_index()
rfm["recency"] = (ref_date - rfm["last_order"]).dt.days
rfm["R"] = pd.qcut(rfm["recency"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
rfm["F"] = pd.qcut(rfm["freq"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["M"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["rfm_score"] = rfm["R"].astype(str) + rfm["F"].astype(str) + rfm["M"].astype(str)

SEG_MAP = {(5,5):"Champions",(5,4):"Champions",(4,5):"Loyal",(4,4):"Loyal",
           (4,3):"Loyal",(3,5):"Có tiềm năng",(3,4):"Có tiềm năng",
           (5,3):"Mới gần đây",(2,5):"Nguy cơ rời bỏ",(2,4):"Nguy cơ rời bỏ",
           (2,3):"Nguy cơ rời bỏ",(1,5):"Không thể mất",(1,4):"Không thể mất",
           (2,2):"Ngủ đông",(1,3):"Ngủ đông",(1,2):"Đã mất",(1,1):"Đã mất"}
rfm["segment"] = rfm.apply(lambda r: SEG_MAP.get((r.R, r.F), "Trung bình"), axis=1)

SEG_C = {
    "Champions":      "#1D9E75",
    "Loyal":          "#378ADD",
    "Có tiềm năng":   "#7F77DD",
    "Mới gần đây":    "#69b3a2",
    "Nguy cơ rời bỏ": "#f4a261",
    "Không thể mất":  "#D85A30",
    "Ngủ đông":       "#B3B3B3",
    "Đã mất":         "#888780",
    "Trung bình":     "#CCCCCC",
}

fig, ax = plt.subplots(figsize=(13, 7))
for seg, grp in rfm.groupby("segment"):
    sz = grp["monetary"] / rfm["monetary"].max() * 500 + 15
    ax.scatter(grp["freq"], grp["recency"],
               s=sz, c=SEG_C.get(seg, "#AAAAAA"),
               alpha=0.65, label=f"{seg} ({len(grp)})",
               edgecolors="white", linewidths=0.5, zorder=3)

ax.invert_yaxis()
ax.legend(loc="upper right", framealpha=0.9, fontsize=9,
          ncol=2, edgecolor=GREY82)
apply_gallery_style(ax,
    title="Phân tích RFM — 702 đại lý",
    subtitle="Kích thước ~ Doanh thu  |  Trục X: Tần suất đặt hàng  |  Trục Y: Recency (ngày, nhỏ = gần đây)",
    xlabel="Tần suất đặt hàng (số đơn)",
    ylabel="Recency (ngày từ lần mua cuối)")
add_watermark(ax)
add_top_bar(fig)
_save(fig, "04_rfm_scatter.png")


# ════════════════════════════════════════════════════════════════════════════
# CHART 05 — Top 20 tỉnh (Economist horizontal bar)
# Ref: web-horizontal-barplot-with-labels-the-economist.ipynb
# ════════════════════════════════════════════════════════════════════════════
print("📊  Chart 05 — Top 20 tỉnh doanh thu...")

by_prov = (fact.groupby(["province_name", "region"])["line_total"]
           .sum().reset_index()
           .nlargest(20, "line_total"))
by_prov = by_prov.sort_values("line_total")

fig, ax = plt.subplots(figsize=(13, 8))
fig.patch.set_facecolor(BG_WHITE)
ax.set_facecolor(BG_WHITE)

colors_p = [REGION_COLORS.get(r, GREY70) for r in by_prov["region"]]
y_pos = range(len(by_prov))
bars = ax.barh(y_pos, by_prov["line_total"].values / 1e9,
               color=colors_p, height=0.65, edgecolor=BG_WHITE, linewidth=2)

ax.set_axisbelow(True)
ax.grid(axis="x", color=GREY91, lw=1.0)
ax.set_yticks([])
ax.xaxis.set_tick_params(labeltop=True, labelbottom=False, length=0, labelsize=10)

for bar, name, region, val in zip(bars, by_prov["province_name"],
                                   by_prov["region"], by_prov["line_total"]):
    x_lbl = 0.15
    ax.text(x_lbl, bar.get_y() + bar.get_height() / 2,
            name, va="center", fontsize=10, color="white", fontweight="bold",
            path_effects=[__import__("matplotlib.patheffects", fromlist=["withStroke"])
                          .withStroke(linewidth=4, foreground=REGION_COLORS.get(region, GREY70))])
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
            f"{val/1e9:.1f} tỷ", va="center", fontsize=9, color=GREY40)

for sp in ax.spines.values():
    sp.set_visible(False)

fig.subplots_adjust(left=0.02, right=0.92, top=0.88, bottom=0.05)
fig.text(0.02, 0.93, "Top 20 tỉnh thành — Doanh thu tích lũy",
         fontsize=15, fontweight="bold", color="#202020")
fig.text(0.02, 0.895, "T1/2025 – T2/2026  •  đơn vị: tỷ đồng",
         fontsize=11, color=GREY40)

# Legend vùng miền
handles = [mpatches.Patch(color=v, label=k) for k, v in REGION_COLORS.items()]
fig.legend(handles=handles, loc="lower right", bbox_to_anchor=(0.95, 0.03),
           framealpha=0.95, fontsize=10, edgecolor=GREY82)
fig.add_artist(mlines.Line2D([0, 1], [0.96, 0.96], lw=3,
                              color=RED_ECO, transform=fig.transFigure))

fig.text(0.95, 0.01, "Xe đạp Thống Nhất  •  DATA EXPLORERS 2026",
         ha="right", fontsize=8, color=GREY70, style="italic")
_save(fig, "05_top20_tinh_doanh_thu.png")


# ════════════════════════════════════════════════════════════════════════════
# CHART 06 — Doanh thu 3 miền theo quý (Stacked area)
# Ref: 243-area-chart-with-white-grid.ipynb + 250-basic-stacked-area-chart.ipynb
# ════════════════════════════════════════════════════════════════════════════
print("📊  Chart 06 — Doanh thu 3 miền theo quý...")

by_reg = (fact.groupby(["fiscal_year", "fiscal_quarter", "region"])["line_total"]
          .sum().reset_index())
by_reg["q_n"] = (by_reg["fiscal_year"] - 2025) * 4 + by_reg["fiscal_quarter"]
by_reg["q_label"] = by_reg.apply(
    lambda r: f"Q{int(r.fiscal_quarter)}/{str(int(r.fiscal_year))[2:]}", axis=1)
pivot_r = by_reg.pivot_table(index=["q_n", "q_label"], columns="region",
                              values="line_total", fill_value=0).reset_index()
pivot_r = pivot_r.sort_values("q_n")
q_labels = pivot_r["q_label"].tolist()
x = range(len(q_labels))

fig, ax = plt.subplots(figsize=(13, 6))
regions_plot = [r for r in ["Miền Bắc", "Miền Trung", "Miền Nam"] if r in pivot_r.columns]

bottom = np.zeros(len(pivot_r))
for region in regions_plot:
    vals = pivot_r[region].values / 1e9
    ax.bar(x, vals, bottom=bottom, label=region,
           color=REGION_COLORS[region], edgecolor=BG_WHITE, linewidth=2,
           width=0.65, zorder=3)
    # Nhãn bên trong cột nếu đủ lớn
    for i, (v, b) in enumerate(zip(vals, bottom)):
        if v > 1:
            ax.text(i, b + v / 2, f"{v:.1f}", ha="center", va="center",
                    fontsize=9, color="white", fontweight="bold")
    bottom += vals

for i, total in enumerate(bottom):
    ax.text(i, total + 0.3, f"{total:.1f}", ha="center", fontsize=10,
            fontweight="bold", color="#202020")

ax.set_xticks(list(x))
ax.set_xticklabels(q_labels, fontsize=10)
ax.legend(loc="upper left", framealpha=0.9, fontsize=10, edgecolor=GREY82)
apply_gallery_style(ax,
    title="Doanh thu theo vùng miền × Quý",
    subtitle="Giá trị ghi trên mỗi cột: tỷ đồng",
    ylabel="Tỷ đồng")
add_watermark(ax)
add_top_bar(fig, color=REGION_COLORS["Miền Nam"])
_save(fig, "06_doanh_thu_3_mien_quy.png")


# ════════════════════════════════════════════════════════════════════════════
# CHART 07 — Heatmap màu sắc × nhóm SP
# Ref: 91-customize-seaborn-heatmap.ipynb
# ════════════════════════════════════════════════════════════════════════════
print("📊  Chart 07 — Heatmap màu sắc × nhóm SP...")

color_grp = (fact[fact["color"].notna() & (fact["color"] != "")]
             .groupby(["group_code", "color"])["quantity"].sum().reset_index())
top_colors = (color_grp.groupby("color")["quantity"].sum()
              .nlargest(16).index.tolist())
heat_df = (color_grp[color_grp["color"].isin(top_colors)]
           .pivot_table(index="color", columns="group_code",
                        values="quantity", fill_value=0)
           .reindex(columns=[g for g in GROUP_ORDER if g in color_grp["group_code"].unique()])
           .rename(columns=BRAND_LABELS))
heat_df = heat_df.loc[heat_df.sum(axis=1).sort_values(ascending=False).index]

fig, ax = plt.subplots(figsize=(11, 8))
sns.heatmap(heat_df / 1000,
            annot=True, fmt=".1f",
            annot_kws={"size": 9, "color": "#202020"},
            cmap="YlOrRd",
            linewidths=2, linecolor=BG_WHITE,
            cbar_kws={"label": "Nghìn chiếc", "shrink": 0.8},
            ax=ax)
ax.set_xlabel("Nhóm sản phẩm", fontsize=11, labelpad=8)
ax.set_ylabel("Màu sắc", fontsize=11, labelpad=8)
ax.set_title("Heatmap: Sản lượng màu sắc × nhóm sản phẩm\n"
             "Đơn vị: nghìn chiếc  |  T1/2025 – T2/2026",
             fontsize=13, fontweight="bold", loc="left", pad=12)
ax.tick_params(length=0, labelsize=10)
ax.figure.patch.set_facecolor(BG_WHITE)
add_watermark(ax)
add_top_bar(fig, color=BRAND["KIDBIKE_2"])
_save(fig, "07_heatmap_mau_nhom_sp.png")


# ════════════════════════════════════════════════════════════════════════════
# CHART 08 — Tăng trưởng MoM (Bar + Line dual axis)
# Ref: line-chart-dual-y-axis-with-matplotlib.ipynb
# ════════════════════════════════════════════════════════════════════════════
print("📊  Chart 08 — Tăng trưởng MoM...")

monthly_all = (fact.groupby(["fiscal_year", "fiscal_month"])["line_total"]
               .sum().reset_index().sort_values(["fiscal_year", "fiscal_month"]))
monthly_all["ym_n"] = (monthly_all["fiscal_year"] - 2025) * 12 + monthly_all["fiscal_month"]
monthly_all["ym_label"] = monthly_all.apply(
    lambda r: f"T{int(r.fiscal_month)}/{str(int(r.fiscal_year))[2:]}", axis=1)
monthly_all["mom_pct"] = monthly_all["line_total"].pct_change() * 100

COLOR_BAR  = "#69b3a2"
COLOR_LINE = "#e85252"

fig, ax1 = plt.subplots(figsize=(13, 6))
ax2 = ax1.twinx()

bars = ax1.bar(monthly_all["ym_n"], monthly_all["line_total"] / 1e9,
               color=COLOR_BAR, alpha=0.75, width=0.7, zorder=3, label="Doanh thu")
ax2.plot(monthly_all["ym_n"], monthly_all["mom_pct"],
         color=COLOR_LINE, lw=2.5, marker="D", markersize=6,
         markerfacecolor="white", markeredgewidth=2, zorder=4, label="Tăng trưởng MoM")
ax2.axhline(0, color=GREY82, lw=1, ls="--")

for bar, pct in zip(bars, monthly_all["mom_pct"]):
    if pd.notna(pct):
        color = COLOR_LINE if pct >= 0 else "#D85A30"
        ax2.text(bar.get_x() + bar.get_width() / 2,
                 pct + (2 if pct >= 0 else -5),
                 f"{pct:+.0f}%", ha="center", fontsize=8, color=color, fontweight="bold")

ax1.set_xticks(monthly_all["ym_n"].tolist())
ax1.set_xticklabels(monthly_all["ym_label"].tolist(), fontsize=10)
ax1.set_ylabel("Doanh thu (tỷ đồng)", color=COLOR_BAR, fontsize=11)
ax1.tick_params(axis="y", labelcolor=COLOR_BAR, length=0)
ax2.set_ylabel("Tăng trưởng MoM (%)", color=COLOR_LINE, fontsize=11)
ax2.tick_params(axis="y", labelcolor=COLOR_LINE, length=0)

apply_gallery_style(ax1,
    title="Doanh thu hàng tháng & Tăng trưởng MoM",
    subtitle="Thanh xanh: Doanh thu (tỷ đồng)  |  Đường đỏ: % thay đổi so tháng trước",
    remove_spines=("top",), grid_axis="y")
ax1.figure.patch.set_facecolor(BG_WHITE)
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2,
           loc="upper left", framealpha=0.9, fontsize=10)
add_watermark(ax1)
add_top_bar(fig, color=COLOR_BAR)
_save(fig, "08_tang_truong_mom.png")


# ════════════════════════════════════════════════════════════════════════════
# CHART 09 — Pareto đại lý
# Ref: 120-line-chart-with-matplotlib.ipynb + 1-basic-barplot.ipynb
# ════════════════════════════════════════════════════════════════════════════
print("📊  Chart 09 — Pareto đại lý...")

dealer_rev = (fact.groupby("customer_code")["line_total"].sum()
              .sort_values(ascending=False).reset_index())
dealer_rev["rank"] = range(1, len(dealer_rev) + 1)
dealer_rev["cumulative_pct"] = dealer_rev["line_total"].cumsum() / dealer_rev["line_total"].sum() * 100

idx_80 = (dealer_rev["cumulative_pct"] >= 80).idxmax()

fig, ax1 = plt.subplots(figsize=(13, 6))
ax2 = ax1.twinx()

bar_colors = ["#1D9E75" if i <= idx_80 else GREY70
              for i in range(len(dealer_rev))]
ax1.bar(dealer_rev["rank"], dealer_rev["line_total"] / 1e6,
        color=bar_colors, width=1.0, zorder=2)
ax2.plot(dealer_rev["rank"], dealer_rev["cumulative_pct"],
         color="#D85A30", lw=2.5, zorder=4)
ax2.axhline(80, color=GREY82, lw=1.2, ls="--")
ax2.text(dealer_rev["rank"].max() * 0.98, 81.5, "80%",
         ha="right", fontsize=10, color="#D85A30", fontweight="bold")

ax1.axvline(idx_80 + 1, color="#D85A30", lw=1.5, ls="--", alpha=0.7)
ax1.text(idx_80 + 2, dealer_rev["line_total"].max() / 1e6 * 0.85,
         f"Top {idx_80+1} đại lý\n→ 80% doanh thu",
         fontsize=9, color="#D85A30", fontweight="bold")

ax1.set_xlabel("Xếp hạng đại lý (theo doanh thu)", fontsize=11)
ax1.set_ylabel("Doanh thu (triệu đồng)", color="#1D9E75", fontsize=11)
ax1.tick_params(axis="y", labelcolor="#1D9E75", length=0)
ax2.set_ylabel("Doanh thu tích lũy (%)", color="#D85A30", fontsize=11)
ax2.tick_params(axis="y", labelcolor="#D85A30", length=0)
ax2.set_ylim(0, 105)
apply_gallery_style(ax1,
    title="Phân tích Pareto — Đóng góp doanh thu của đại lý",
    subtitle="Xanh: nằm trong Top 80%  |  Xám: dưới ngưỡng",
    remove_spines=("top",), grid_axis="y")
ax1.figure.patch.set_facecolor(BG_WHITE)
add_watermark(ax1)
add_top_bar(fig, color="#1D9E75")
_save(fig, "09_pareto_dai_ly.png")


# ════════════════════════════════════════════════════════════════════════════
# CHART 10 — Phân khúc RFM (Horizontal grouped bar)
# Ref: 11-grouped-barplot.ipynb
# ════════════════════════════════════════════════════════════════════════════
print("📊  Chart 10 — Phân khúc RFM...")

seg_stats = rfm.groupby("segment").agg(
    count=("customer_code", "count"),
    total_rev=("monetary", "sum")
).reset_index().sort_values("total_rev", ascending=True)

fig, (ax_c, ax_r) = plt.subplots(1, 2, figsize=(14, 6))
fig.patch.set_facecolor(BG_WHITE)

seg_colors = [SEG_C.get(s, GREY70) for s in seg_stats["segment"]]
y_p = range(len(seg_stats))

ax_c.barh(y_p, seg_stats["count"], color=seg_colors, height=0.6,
           edgecolor=BG_WHITE, linewidth=2)
for i, (v, s) in enumerate(zip(seg_stats["count"], seg_stats["segment"])):
    ax_c.text(v + 1, i, f"{v}", va="center", fontsize=10, color=GREY40)
ax_c.set_yticks(list(y_p))
ax_c.set_yticklabels(seg_stats["segment"], fontsize=10)
apply_gallery_style(ax_c, title="Số lượng đại lý", xlabel="Số đại lý",
                    remove_spines=("top","right","bottom"), grid_axis="x")

ax_r.barh(y_p, seg_stats["total_rev"] / 1e9, color=seg_colors, height=0.6,
           edgecolor=BG_WHITE, linewidth=2)
for i, v in enumerate(seg_stats["total_rev"]):
    ax_r.text(v / 1e9 + 0.2, i, f"{v/1e9:.1f} tỷ", va="center",
              fontsize=10, color=GREY40)
ax_r.set_yticks([])
apply_gallery_style(ax_r, title="Doanh thu theo phân khúc", xlabel="Tỷ đồng",
                    remove_spines=("top","right","bottom","left"), grid_axis="x")
add_watermark(ax_r)
add_top_bar(fig, color=SEG_C["Champions"])
_save(fig, "10_rfm_segments.png")


# ════════════════════════════════════════════════════════════════════════════
# CHART 11 — So sánh Q1/2025 vs Q1/2026
# Ref: 11-grouped-barplot.ipynb + line overlay
# ════════════════════════════════════════════════════════════════════════════
print("📊  Chart 11 — So sánh Q1/2025 vs Q1/2026...")

q1_cmp = {}
for yr in [2025, 2026]:
    sub = fact[(fact.fiscal_year == yr) & (fact.fiscal_quarter == 1)]
    q1_cmp[yr] = sub.groupby("group_code")["line_total"].sum().reindex(GROUP_ORDER).fillna(0)
cmp_df = pd.DataFrame(q1_cmp).fillna(0)
cmp_df["yoy_pct"] = ((cmp_df[2026] - cmp_df[2025]) / cmp_df[2025].replace(0, 1)) * 100
labels_cmp = [BRAND_LABELS[g] for g in GROUP_ORDER]

x = np.arange(len(GROUP_ORDER))
width = 0.35

fig, ax1 = plt.subplots(figsize=(13, 6))
ax2 = ax1.twinx()
b1 = ax1.bar(x - width / 2, cmp_df[2025].values / 1e9, width,
             color=[BRAND[g] for g in GROUP_ORDER], alpha=0.5,
             edgecolor="white", label="Q1/2025")
b2 = ax1.bar(x + width / 2, cmp_df[2026].values / 1e9, width,
             color=[BRAND[g] for g in GROUP_ORDER],
             edgecolor="white", label="Q1/2026")
ax2.plot(x, cmp_df["yoy_pct"].values, color="#D85A30",
         lw=2.5, marker="D", markersize=8, markerfacecolor="white",
         markeredgewidth=2, zorder=5, label="YoY %")
ax2.axhline(0, color=GREY82, lw=1, ls="--")
for xi, pct in zip(x, cmp_df["yoy_pct"].values):
    color = "#1D9E75" if pct >= 0 else "#D85A30"
    ax2.text(xi, pct + (3 if pct >= 0 else -6), f"{pct:+.0f}%",
             ha="center", fontsize=10, color=color, fontweight="bold")

ax1.set_xticks(x)
ax1.set_xticklabels(labels_cmp, fontsize=10)
ax1.set_ylabel("Doanh thu Q1 (tỷ đồng)", fontsize=11)
ax2.set_ylabel("Tăng trưởng YoY (%)", color="#D85A30", fontsize=11)
ax1.tick_params(length=0)
ax2.tick_params(axis="y", labelcolor="#D85A30", length=0)
lines1, l1 = ax1.get_legend_handles_labels()
lines2, l2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, l1 + l2, loc="upper right",
           framealpha=0.9, fontsize=10)
apply_gallery_style(ax1,
    title="So sánh Q1/2025 vs Q1/2026 — từng nhóm SP",
    subtitle="Đường đỏ: % tăng trưởng YoY  |  Màu nhạt: 2025  |  Màu đậm: 2026",
    remove_spines=("top",), grid_axis="y")
ax1.figure.patch.set_facecolor(BG_WHITE)
add_watermark(ax1)
add_top_bar(fig, color=BRAND["SPORTBIKE_S"])
_save(fig, "11_so_sanh_q1_2025_2026.png")


# ════════════════════════════════════════════════════════════════════════════
# CHART 12 — Top 20 SKU (Lollipop)
# Ref: web-lollipop-plot-with-python-the-office.ipynb (simplified)
# ════════════════════════════════════════════════════════════════════════════
print("📊  Chart 12 — Top 20 SKU (Lollipop)...")

by_sku = (fact.groupby(["product_code", "product_name", "color", "group_code"])
          .agg(so_luong=("quantity", "sum"), doanh_thu=("line_total", "sum"))
          .reset_index().nlargest(20, "doanh_thu")
          .sort_values("doanh_thu"))
by_sku["ten_ngan"] = by_sku.apply(
    lambda r: f"{r.product_name[:22]} ({r.color})" if r.color else r.product_name[:28], axis=1)

fig, ax = plt.subplots(figsize=(13, 9))
fig.patch.set_facecolor(BG_WHITE)
ax.set_facecolor(BG_AXES)

y_p = range(len(by_sku))
dot_colors = [BRAND.get(g, GREY70) for g in by_sku["group_code"]]

# Vlines tham chiếu ngang
for yi in y_p:
    ax.axhline(yi, color="white", lw=1.5, zorder=1)

ax.hlines(y_p, 0, by_sku["doanh_thu"].values / 1e9,
          color=dot_colors, lw=2.5, zorder=2)
ax.scatter(by_sku["doanh_thu"].values / 1e9, list(y_p),
           color=dot_colors, s=90, zorder=3, edgecolors="white", linewidths=1.5)

for yi, (_, row) in enumerate(by_sku.iterrows()):
    ax.text(-0.3, yi, row["ten_ngan"], va="center", ha="right",
            fontsize=9, color="#202020")
    ax.text(row["doanh_thu"] / 1e9 + 0.15, yi,
            f"{row['doanh_thu']/1e9:.1f} tỷ  ({int(row['so_luong'])} chiếc)",
            va="center", fontsize=8.5, color=GREY40)

ax.set_xlim(-18, by_sku["doanh_thu"].max() / 1e9 * 1.35)
ax.set_yticks([])
ax.tick_params(axis="x", length=0, labelsize=9)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.set_axisbelow(True)
ax.grid(axis="x", color="white", lw=1.5)
ax.set_title("Top 20 SKU bán chạy nhất — T1/2025 – T2/2026",
             fontsize=14, fontweight="bold", loc="left", pad=12, color="#202020")
ax.set_xlabel("Doanh thu (tỷ đồng)", fontsize=11, color=GREY40)

lg = legend_patches()
ax.legend(handles=lg, loc="lower right", framealpha=0.92, fontsize=9, edgecolor=GREY82)
add_watermark(ax)
add_top_bar(fig, color=BRAND["KIDBIKE_1"])
_save(fig, "12_top20_sku.png")


# ════════════════════════════════════════════════════════════════════════════
# CHART 13 — Dự báo Prophet Q2/2026 (Area + confidence band)
# Ref: web-area-chart-with-different-colors-for-positive-and-negative-values.ipynb
# ════════════════════════════════════════════════════════════════════════════
print("📊  Chart 13 — Dự báo Prophet Q2/2026...")

from analytics.forecasting.demand_forecast import prepare_series, forecast_group

fig, axes = plt.subplots(2, 3, figsize=(16, 9))
fig.patch.set_facecolor(BG_WHITE)
all_axes = axes.flatten()

forecast_results = {}
for i, grp in enumerate(GROUP_ORDER):
    ax = all_axes[i]
    ax.set_facecolor(BG_AXES)
    color = BRAND[grp]
    color_fc = "#D85A30"

    ts = prepare_series(fact, grp)
    try:
        fc = forecast_group(ts, periods=91)
    except Exception as e:
        ax.text(0.5, 0.5, f"Lỗi: {e}", transform=ax.transAxes,
                ha="center", color="red")
        continue

    forecast_results[grp] = fc

    # Dữ liệu lịch sử
    ax.plot(ts["ds"], ts["y"] / 1e9, color=color, lw=1.8, alpha=0.8,
            label="Lịch sử", zorder=3)
    ax.fill_between(ts["ds"], 0, ts["y"] / 1e9, color=color, alpha=0.15, zorder=2)

    # Dự báo Q2
    q2 = fc[(fc["ds"] >= "2026-04-01") & (fc["ds"] <= "2026-06-30")]
    ax.plot(q2["ds"], q2["yhat"] / 1e9, color=color_fc, lw=2.2,
            label="Dự báo Q2", zorder=4)
    ax.fill_between(q2["ds"],
                    q2["yhat_lower"] / 1e9,
                    q2["yhat_upper"] / 1e9,
                    color=color_fc, alpha=0.18, label="Khoảng 80%", zorder=2)

    # Đường phân cách lịch sử / dự báo
    ax.axvline(pd.Timestamp("2026-03-01"), color=GREY82, lw=1.2, ls="--", zorder=5)
    ax.text(pd.Timestamp("2026-03-02"),
            ax.get_ylim()[1] * 0.9 if ax.get_ylim()[1] > 0 else 1,
            "Q2\ndự báo", fontsize=8, color=color_fc, fontweight="bold")

    q2_total = q2["yhat"].sum()
    ax.set_title(f"{BRAND_LABELS[grp]}\n→ Q2: {q2_total/1e9:.1f} tỷ",
                 fontsize=10, fontweight="bold", loc="left", color="#202020")
    ax.tick_params(length=0, labelsize=8)
    ax.set_axisbelow(True)
    ax.grid(color="white", lw=1.5, alpha=0.9)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    for sp in ["left", "bottom"]:
        ax.spines[sp].set_color(GREY82)
    if i == 0:
        ax.legend(fontsize=8, framealpha=0.9, loc="upper left")

# Ô thứ 6: tổng hợp
ax_sum = all_axes[5]
ax_sum.set_facecolor(BG_AXES)
total_vals = {}
for grp, fc in forecast_results.items():
    q2 = fc[(fc["ds"] >= "2026-04-01") & (fc["ds"] <= "2026-06-30")]
    total_vals[grp] = (q2["yhat"].sum(), q2["yhat_lower"].sum(), q2["yhat_upper"].sum())

grp_names = [BRAND_LABELS[g] for g in total_vals]
mids  = [total_vals[g][0] / 1e9 for g in total_vals]
lows  = [total_vals[g][1] / 1e9 for g in total_vals]
highs = [total_vals[g][2] / 1e9 for g in total_vals]
x_sum = range(len(grp_names))
bars_s = ax_sum.bar(x_sum, mids, color=[BRAND[g] for g in total_vals],
                     edgecolor="white", zorder=3)
ax_sum.errorbar(x_sum, mids,
                yerr=[np.array(mids) - np.array(lows),
                       np.array(highs) - np.array(mids)],
                fmt="none", color=GREY40, capsize=5, lw=1.5, zorder=4)
for xi, (mid, high) in enumerate(zip(mids, highs)):
    ax_sum.text(xi, high + 1, f"{mid:.0f} tỷ", ha="center",
                fontsize=9, fontweight="bold", color="#202020")
ax_sum.set_xticks(list(x_sum))
ax_sum.set_xticklabels(grp_names, rotation=30, ha="right", fontsize=9)
ax_sum.set_title("Tổng hợp dự báo Q2/2026", fontsize=10, fontweight="bold", loc="left")
ax_sum.tick_params(length=0)
ax_sum.set_axisbelow(True)
ax_sum.grid(axis="y", color="white", lw=1.5)
for sp in ["top", "right"]:
    ax_sum.spines[sp].set_visible(False)

fig.suptitle("Dự báo doanh số Q2/2026 — Mô hình Facebook Prophet",
             fontsize=14, fontweight="bold", y=1.01, x=0.02, ha="left", color="#202020")
fig.text(0.02, 0.99,
         "Dữ liệu train: T1/2025 – T2/2026  |  Khoảng tin cậy 80%  |  Logistic growth với floor=0",
         fontsize=10, color=GREY40, ha="left")
fig.tight_layout()
add_top_bar(fig, color=BRAND["SPORTBIKE_S"])
_save(fig, "13_du_bao_prophet_q2_2026.png")


# ════════════════════════════════════════════════════════════════════════════
# CHART 14 — Dự báo màu sắc Q2/2026 (Grouped horizontal bar)
# Ref: 11-grouped-barplot.ipynb + web-horizontal-barplot-with-labels
# ════════════════════════════════════════════════════════════════════════════
print("📊  Chart 14 — Dự báo màu sắc Q2/2026...")

from analytics.forecasting.color_forecast import forecast_color_q2

color_fc_df = forecast_color_q2(fact)
top_n = 6
fig, axes = plt.subplots(1, len(GROUP_ORDER), figsize=(18, 7), sharey=False)
fig.patch.set_facecolor(BG_WHITE)

for i, grp in enumerate(GROUP_ORDER):
    ax = axes[i]
    ax.set_facecolor(BG_AXES)
    sub = color_fc_df[color_fc_df["group_code"] == grp].head(top_n)
    if sub.empty:
        ax.set_visible(False)
        continue

    color_base = BRAND[grp]
    y_p = range(len(sub))
    bars = ax.barh(list(y_p), sub["du_bao_q2_pct"].values,
                   color=color_base, alpha=0.82,
                   edgecolor=BG_WHITE, linewidth=2, height=0.6)
    ax.set_yticks(list(y_p))
    ax.set_yticklabels(sub["color"].values, fontsize=9)
    ax.invert_yaxis()
    for bar, pct in zip(bars, sub["du_bao_q2_pct"].values):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{pct:.1f}%", va="center", fontsize=9, color=GREY40)

    ax.set_xlim(0, sub["du_bao_q2_pct"].max() * 1.4)
    ax.set_title(BRAND_LABELS[grp], fontsize=11, fontweight="bold",
                 loc="center", color=color_base, pad=10)
    ax.set_xlabel("Tỷ trọng dự báo Q2 (%)", fontsize=9, color=GREY40)
    ax.tick_params(length=0, labelsize=9)
    ax.set_axisbelow(True)
    ax.grid(axis="x", color="white", lw=1.5)
    for sp in ["top", "right", "bottom"]:
        ax.spines[sp].set_visible(False)
    ax.spines["left"].set_color(GREY82)

fig.suptitle("Dự báo tỷ trọng màu sắc Q2/2026",
             fontsize=14, fontweight="bold", x=0.02, ha="left", y=1.02)
fig.text(0.02, 0.985,
         "Phương pháp: Weighted Moving Average (T1–T3/2026)  |  Top 6 màu mỗi nhóm",
         fontsize=10, color=GREY40)
fig.tight_layout()
add_top_bar(fig, color=BRAND["KIDBIKE_2"])
_save(fig, "14_du_bao_mau_sac_q2.png")


# ════════════════════════════════════════════════════════════════════════════
# CHART 15 — Churn risk (Lollipop với màu risk)
# Ref: web-lollipop-plot-with-python-the-office.ipynb
# ════════════════════════════════════════════════════════════════════════════
print("📊  Chart 15 — Dự báo churn đại lý...")

from analytics.forecasting.dealer_forecast import (
    build_dealer_features, label_churn, train_churn_model
)
cus_name = (fact[["customer_code", "customer_name"]]
            .drop_duplicates().set_index("customer_code")["customer_name"])

feats = build_dealer_features(fact)
feats = label_churn(feats)
try:
    model, scaler, fp = train_churn_model(feats)
except Exception as e:
    print(f"  Lỗi train model: {e}")
    fp = feats.copy()
    fp["churn_prob"] = 0.0

fp["customer_name"] = fp["customer_code"].map(cus_name).fillna("—")

# Active dealers only, sorted by churn prob
active = fp[fp["churn"] == 0].sort_values("churn_prob", ascending=False).head(30)

def risk_color(p):
    if p >= 0.60: return "#D85A30"
    if p >= 0.35: return "#f4a261"
    return "#69b3a2"

fig, ax = plt.subplots(figsize=(13, 10))
fig.patch.set_facecolor(BG_WHITE)
ax.set_facecolor(BG_AXES)

y_p = range(len(active))
for yi in y_p:
    ax.axhline(yi, color="white", lw=1.5, zorder=1)

dot_c = [risk_color(p) for p in active["churn_prob"].values]
ax.hlines(list(y_p), 0, active["churn_prob"].values * 100,
          color=dot_c, lw=2.5, zorder=2)
ax.scatter(active["churn_prob"].values * 100, list(y_p),
           color=dot_c, s=85, zorder=3, edgecolors="white", linewidths=1.5)

for yi, (_, row) in enumerate(active.iterrows()):
    name_short = str(row["customer_name"])[:32]
    ax.text(-0.3, yi, name_short, va="center", ha="right", fontsize=9, color="#202020")
    ax.text(row["churn_prob"] * 100 + 0.5, yi,
            f"{row['churn_prob']:.0%}  |  {int(row['recency_days'])} ngày  |  "
            f"{row['revenue_total']/1e6:.0f}M",
            va="center", fontsize=8.5, color=GREY40)

ax.set_xlim(-30, 35)
ax.set_yticks([])
ax.tick_params(axis="x", length=0, labelsize=9)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.set_axisbelow(True)
ax.grid(axis="x", color="white", lw=1.5)
ax.set_xlabel("Xác suất churn (%)", fontsize=11, color=GREY40)

# Legend risk levels
risk_handles = [
    mpatches.Patch(color="#D85A30", label="Nguy cơ cao (≥60%)"),
    mpatches.Patch(color="#f4a261", label="Nguy cơ TB (35–60%)"),
    mpatches.Patch(color="#69b3a2", label="Nguy cơ thấp (<35%)"),
]
ax.legend(handles=risk_handles, loc="lower right", framealpha=0.92,
          fontsize=9, edgecolor=GREY82)

# Stats box
n_churned = (fp["churn"] == 1).sum()
n_total   = len(fp)
fig.text(0.75, 0.97,
         f"Đã churn: {n_churned}/{n_total} đại lý ({n_churned/n_total:.0%})\n"
         f"Mô hình: {type(model).__name__}",
         fontsize=10, color=GREY40, ha="left", va="top",
         bbox=dict(boxstyle="round,pad=0.4", facecolor=BG_WHITE, edgecolor=GREY82))

ax.set_title("Dự báo nguy cơ churn — Top 30 đại lý cần chú ý\n"
             "Cột: % churn  |  Recency (ngày)  |  Doanh thu",
             fontsize=13, fontweight="bold", loc="left", pad=12, color="#202020")
add_watermark(ax)
add_top_bar(fig, color="#D85A30")
_save(fig, "15_du_bao_churn_dai_ly.png")


# ════════════════════════════════════════════════════════════════════════════
#  EXCEL — Bảng kết quả tổng hợp
# ════════════════════════════════════════════════════════════════════════════
print("\n📋  Đang xuất bảng kết quả Excel...")
excel_path = TABLE_DIR / "tnbike_ketqua.xlsx"

try:
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:

    # Sheet 1: KPI
    kpi_rows = [
        ["CHỈ SỐ", "GIÁ TRỊ", "ĐƠN VỊ"],
        ["Tổng doanh thu", fact["line_total"].sum(), "VNĐ"],
        ["Tổng doanh thu", fact["line_total"].sum() / 1e9, "Tỷ đồng"],
        ["Tổng đơn hàng", fact["so_number"].nunique(), "Đơn"],
        ["Tổng sản lượng", int(fact["quantity"].sum()), "Chiếc"],
        ["Đại lý hoạt động", fact["customer_code"].nunique(), "Đại lý"],
        ["Giá trị TB/chiếc", fact["line_total"].sum() / fact["quantity"].sum(), "VNĐ"],
        ["Doanh thu TB/đại lý", fact["line_total"].sum() / fact["customer_code"].nunique(), "VNĐ"],
        ["Số tỉnh có doanh số", fact["province_name"].dropna().nunique(), "Tỉnh/TP"],
        ["Tổng SKU được bán", fact["product_code"].nunique(), "SKU"],
    ]
    pd.DataFrame(kpi_rows[1:], columns=kpi_rows[0]).to_excel(
        writer, sheet_name="1. KPI Tổng hợp", index=False)

    # Sheet 2: Doanh thu tháng
    dt_monthly = (fact.groupby(["fiscal_year", "fiscal_month", "group_code", "group_name"])
                  .agg(doanh_thu=("line_total", "sum"), so_luong=("quantity", "sum"),
                       so_don=("so_number", "nunique")).reset_index())
    dt_monthly["ym"] = dt_monthly.apply(
        lambda r: f"T{int(r.fiscal_month)}/{int(r.fiscal_year)}", axis=1)
    dt_monthly.to_excel(writer, sheet_name="2. DT Tháng × Nhóm SP", index=False)

    # Sheet 3: RFM
    rfm_out = rfm[["customer_code", "customer_name", "recency", "freq",
                   "monetary", "R", "F", "M", "rfm_score", "segment"]].copy()
    rfm_out.columns = ["Mã đại lý", "Tên đại lý", "Recency (ngày)", "Tần suất",
                       "Doanh thu", "R", "F", "M", "RFM Score", "Phân khúc"]
    rfm_out.sort_values("Doanh thu", ascending=False).to_excel(
        writer, sheet_name="3. RFM Đại lý", index=False)

    # Sheet 4: Tỉnh thành
    prov_out = (fact.groupby(["province_name", "region"])
                .agg(doanh_thu=("line_total", "sum"),
                     so_luong=("quantity", "sum"),
                     so_don=("so_number", "nunique"),
                     so_dai_ly=("customer_code", "nunique"))
                .reset_index().sort_values("doanh_thu", ascending=False))
    prov_out.columns = ["Tỉnh/TP", "Vùng miền", "Doanh thu (VNĐ)",
                        "Sản lượng", "Số đơn", "Số đại lý"]
    prov_out.to_excel(writer, sheet_name="4. DT Tỉnh Thành", index=False)

    # Sheet 5: BCG
    bcg["bcg_label"] = bcg.apply(
        lambda r: BCG_LABELS[(r.market_share >= med_s, r.growth >= med_g)][0], axis=1)
    bcg_out = bcg[["market_share", "growth", "bcg_label"]].reset_index()
    bcg_out.columns = ["Nhóm SP", "Thị phần 2025 (%)", "Tăng trưởng Q1 YoY (%)", "BCG"]
    bcg_out["Tên nhóm"] = bcg_out["Nhóm SP"].map(BRAND_LABELS)
    bcg_out.to_excel(writer, sheet_name="5. BCG Matrix", index=False)

    # Sheet 6: Top 50 SKU
    top_sku = (fact.groupby(["product_code", "product_name", "color", "group_code", "group_name"])
               .agg(so_luong=("quantity", "sum"), doanh_thu=("line_total", "sum"),
                    gia_tb=("unit_price", "mean"), so_don=("so_number", "nunique"))
               .reset_index().nlargest(50, "doanh_thu"))
    top_sku.columns = ["Mã hàng", "Tên SP", "Màu", "Nhóm", "Tên nhóm",
                        "Sản lượng", "Doanh thu (VNĐ)", "Giá TB", "Số đơn"]
    top_sku.to_excel(writer, sheet_name="6. Top 50 SKU", index=False)

    # Sheet 7: Dự báo Prophet Q2
    fc_rows = []
    for grp, fc in forecast_results.items():
        q2 = fc[(fc["ds"] >= "2026-04-01") & (fc["ds"] <= "2026-06-30")]
        fc_rows.append({
            "Nhóm SP": grp, "Tên nhóm": BRAND_LABELS.get(grp, grp),
            "Dự báo Q2 (tỷ)": round(q2["yhat"].sum() / 1e9, 2),
            "Lower 80% (tỷ)": round(q2["yhat_lower"].sum() / 1e9, 2),
            "Upper 80% (tỷ)": round(q2["yhat_upper"].sum() / 1e9, 2),
        })
    pd.DataFrame(fc_rows).to_excel(writer, sheet_name="7. Dự báo Q2 Prophet", index=False)

    # Sheet 8: Dự báo màu Q2
    color_fc_df.rename(columns={
        "group_code": "Nhóm SP",
        "color": "Màu sắc",
        "du_bao_q2_pct": "Tỷ trọng dự báo Q2 (%)"
    }).to_excel(writer, sheet_name="8. Dự báo Màu Q2", index=False)

    # Sheet 9: Churn risk
    churn_out = fp[["customer_code", "customer_name", "recency_days",
                    "freq_total", "revenue_total", "churn", "churn_prob"]].copy()
    churn_out["churn_prob_pct"] = (churn_out["churn_prob"] * 100).round(1)
    churn_out["risk_level"] = churn_out["churn_prob"].apply(
        lambda p: "Cao" if p >= 0.6 else ("Trung bình" if p >= 0.35 else "Thấp"))
    churn_out.columns = ["Mã đại lý", "Tên đại lý", "Recency (ngày)",
                          "Tần suất", "Doanh thu", "Đã churn",
                          "Xác suất churn", "Xác suất (%)", "Mức độ rủi ro"]
    churn_out.sort_values("Xác suất churn", ascending=False).to_excel(
        writer, sheet_name="9. Churn Risk", index=False)

print("  ✓", excel_path)

# ════════════════════════════════════════════════════════════════════════════
print(f"""
{'='*62}
✅  HOÀN THÀNH — 15 biểu đồ + Excel 9 sheets
{'='*62}
📁  Charts  ({CHART_DIR}):""")
for f in sorted(CHART_DIR.glob("*.png")):
    print(f"    {f.name}")
print(f"""
📊  Excel  ({excel_path}):
    Sheet 1–6:  KPI, DT tháng, RFM, Tỉnh, BCG, SKU
    Sheet 7–9:  Dự báo Prophet, Màu Q2, Churn Risk
{'='*62}""")
