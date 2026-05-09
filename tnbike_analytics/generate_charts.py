"""
Sinh toàn bộ biểu đồ và bảng kết quả — Xe đạp Thống Nhất 2025–T2/2026
Chạy: python generate_charts.py
Output:
  output/charts/  → 12 file PNG (300 dpi)
  output/tables/  → tnbike_ketqua.xlsx (7 sheet)
Không cần PostgreSQL — đọc thẳng từ sql/02_import_data.sql
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec
import seaborn as sns
from pathlib import Path
from datetime import datetime

from analytics.sql_data_loader import load_all, build_fact

# ─── Output dirs ──────────────────────────────────────────────────────────────
CHART_DIR = Path("output/charts")
TABLE_DIR = Path("output/tables")
CHART_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)

# ─── Brand colors ─────────────────────────────────────────────────────────────
C = {
    "CITYBIKE_P":  "#1D9E75",
    "KIDBIKE_1":   "#378ADD",
    "KIDBIKE_2":   "#7F77DD",
    "SPORTBIKE_S": "#D85A30",
    "SPORTBIKE_A": "#BA7517",
}
GLABELS = {
    "CITYBIKE_P":  "Xe phổ thông",
    "KIDBIKE_1":   "Xe trẻ em N1",
    "KIDBIKE_2":   "Xe trẻ em N2",
    "SPORTBIKE_S": "Xe TT thép",
    "SPORTBIKE_A": "Xe TT nhôm",
}
RC = {
    "Miền Bắc":  "#378ADD",
    "Miền Trung": "#BA7517",
    "Miền Nam":  "#1D9E75",
}
SEG_C = {
    "Champions":      "#1D9E75",
    "Loyal":          "#378ADD",
    "Có tiềm năng":   "#7F77DD",
    "Mới gần đây":    "#4DA6A0",
    "Cần chú ý":      "#F0A500",
    "Nguy cơ rời bỏ": "#D85A30",
    "Không thể mất":  "#E87040",
    "Ngủ đông":       "#888780",
    "Đã mất":         "#E24B4A",
    "Trung bình":     "#AAAAAA",
}

GROUP_ORDER = ["CITYBIKE_P", "KIDBIKE_1", "KIDBIKE_2", "SPORTBIKE_S", "SPORTBIKE_A"]

# ─── Style toàn cục ────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor":  "white",
    "axes.facecolor":    "#FAFAFA",
    "axes.grid":         True,
    "grid.color":        "#E0E0E0",
    "grid.linewidth":    0.7,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "font.size":         11,
    "axes.titlesize":    14,
    "axes.titleweight":  "bold",
    "axes.labelsize":    11,
    "xtick.labelsize":   10,
    "ytick.labelsize":   10,
    "legend.fontsize":   10,
})

def _fmt_ty(x, _=None):
    return f"{x/1e9:.1f} tỷ" if x >= 1e9 else f"{x/1e6:.0f}M"

def _save(fig, name, tight=True):
    p = CHART_DIR / name
    if tight:
        fig.tight_layout()
    fig.savefig(p, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {p.name}")

def _watermark(ax, text="Xe đạp Thống Nhất | DATA EXPLORERS 2026"):
    ax.annotate(text, xy=(1, -0.08), xycoords="axes fraction",
                ha="right", va="top", fontsize=8, color="#BBBBBB",
                style="italic")


# ══════════════════════════════════════════════════════════════════════════════
#  LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════
print("⏳  Đang tải dữ liệu từ SQL...")
dfs  = load_all()
fact = build_fact(dfs)
fact["order_date"] = pd.to_datetime(fact["order_date"])
fact["ym_label"]   = fact.apply(lambda r: f"T{int(r.fiscal_month)}/{str(int(r.fiscal_year))[2:]}", axis=1)
print(f"    → {len(fact):,} dòng bán hàng | {fact['so_number'].nunique():,} đơn hàng | "
      f"{fact['customer_code'].nunique():,} đại lý\n")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 01 — Doanh thu theo tháng × Nhóm sản phẩm  (Line chart)
# Lấy cảm hứng từ R1 ecommerce_sales_insights: monthly revenue by category
# ══════════════════════════════════════════════════════════════════════════════
print("📊  Chart 01 — Xu hướng doanh thu theo tháng...")
monthly = (fact.groupby(["fiscal_year","fiscal_month","group_code"])
           ["line_total"].sum().reset_index())
monthly["sort_key"] = monthly.fiscal_year*100 + monthly.fiscal_month
monthly["ym"] = monthly.apply(lambda r: f"T{int(r.fiscal_month)}/{str(int(r.fiscal_year))[2:]}", axis=1)
monthly = monthly.sort_values("sort_key")
ym_order = monthly["ym"].unique()

fig, ax = plt.subplots(figsize=(15, 6))
for gc in GROUP_ORDER:
    sub = monthly[monthly.group_code == gc]
    sub = sub.set_index("ym").reindex(ym_order)
    ax.plot(ym_order, sub["line_total"].values / 1e9,
            marker="o", markersize=5, linewidth=2.2,
            label=GLABELS[gc], color=C[gc])
ax.set_title("Doanh thu theo tháng theo nhóm sản phẩm\nT1/2025 – T2/2026", pad=12)
ax.set_ylabel("Doanh thu (tỷ đồng)")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.1f}"))
ax.set_xticks(range(len(ym_order)))
ax.set_xticklabels(ym_order, rotation=45, ha="right")
ax.legend(loc="upper left", framealpha=0.8)
_watermark(ax)
_save(fig, "01_doanh_thu_theo_thang.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 02 — Cơ cấu nhóm sản phẩm  (Donut chart)
# Lấy cảm hứng từ R1: category pie/donut
# ══════════════════════════════════════════════════════════════════════════════
print("📊  Chart 02 — Cơ cấu nhóm sản phẩm...")
by_group = (fact.groupby("group_code")["line_total"].sum()
            .reindex(GROUP_ORDER).fillna(0))
total_rev = by_group.sum()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6))
wedges, texts, autotexts = ax1.pie(
    by_group.values,
    labels=[GLABELS[g] for g in GROUP_ORDER],
    colors=[C[g] for g in GROUP_ORDER],
    autopct="%1.1f%%", pctdistance=0.75,
    startangle=90, wedgeprops=dict(width=0.55, edgecolor="white", linewidth=2),
)
for at in autotexts:
    at.set_fontsize(10); at.set_fontweight("bold")
ax1.set_title("Tỷ trọng doanh thu\ntheo nhóm sản phẩm", fontsize=13, fontweight="bold")

# Bar bên phải
rev_sorted = by_group.sort_values(ascending=True)
bars = ax2.barh([GLABELS[g] for g in rev_sorted.index],
                rev_sorted.values / 1e9,
                color=[C[g] for g in rev_sorted.index],
                edgecolor="white", linewidth=1.2, height=0.6)
for bar, val in zip(bars, rev_sorted.values):
    ax2.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
             f"{val/1e9:.1f} tỷ", va="center", fontsize=10)
ax2.set_xlabel("Doanh thu (tỷ đồng)")
ax2.set_title("Doanh thu tuyệt đối\ntheo nhóm sản phẩm", fontsize=13, fontweight="bold")
ax2.set_xlim(0, rev_sorted.max() / 1e9 * 1.2)
fig.suptitle(f"Tổng doanh thu: {total_rev/1e9:.1f} tỷ đồng  |  T1/2025 – T2/2026",
             fontsize=11, color="#555555", y=0.02)
_save(fig, "02_co_cau_nhom_sp.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 03 — BCG Matrix  (Scatter)
# Lấy cảm hứng từ R1: product portfolio matrix
# ══════════════════════════════════════════════════════════════════════════════
print("📊  Chart 03 — BCG Matrix...")
rev_2025    = fact[fact.fiscal_year==2025].groupby("group_code")["line_total"].sum()
rev_q1_2026 = fact[(fact.fiscal_year==2026)&(fact.fiscal_quarter==1)].groupby("group_code")["line_total"].sum()
rev_q1_2025 = fact[(fact.fiscal_year==2025)&(fact.fiscal_quarter==1)].groupby("group_code")["line_total"].sum()
bcg = pd.DataFrame({"rev_2025": rev_2025, "rev_q1_26": rev_q1_2026, "rev_q1_25": rev_q1_2025}).fillna(0)
bcg["market_share"] = bcg["rev_2025"] / bcg["rev_2025"].sum() * 100
bcg["growth"]       = ((bcg["rev_q1_26"] - bcg["rev_q1_25"]) / bcg["rev_q1_25"].replace(0,1)) * 100

med_s = bcg["market_share"].median()
med_g = bcg["growth"].median()

def _bcg_label(r):
    hs = r.market_share >= med_s; hg = r.growth >= med_g
    if hs and hg:   return "Stars"
    if hs:          return "Cash Cows"
    if hg:          return "Question Marks"
    return "Dogs"

bcg["label"] = bcg.apply(_bcg_label, axis=1)
BCG_C = {"Stars":"#BA7517","Cash Cows":"#1D9E75","Question Marks":"#378ADD","Dogs":"#888780"}

fig, ax = plt.subplots(figsize=(10, 7))
for gc in GROUP_ORDER:
    if gc not in bcg.index: continue
    r = bcg.loc[gc]
    color = BCG_C[r.label]
    size  = max(200, r.rev_2025 / 1e9 * 30)
    ax.scatter(r.market_share, r.growth, s=size, color=color, alpha=0.85,
               zorder=5, edgecolors="white", linewidths=1.5)
    ax.annotate(GLABELS[gc],
                xy=(r.market_share, r.growth),
                xytext=(6, 6), textcoords="offset points",
                fontsize=10, fontweight="bold", color=color)
ax.axvline(med_s, color="#AAAAAA", linestyle="--", linewidth=1)
ax.axhline(med_g, color="#AAAAAA", linestyle="--", linewidth=1)
# Nhãn 4 ô
ax.text(bcg["market_share"].max()*0.88, bcg["growth"].max()*0.88, "Stars",
        fontsize=10, color="#BA7517", alpha=0.6, fontweight="bold")
ax.text(bcg["market_share"].max()*0.88, bcg["growth"].min()*1.1, "Cash Cows",
        fontsize=10, color="#1D9E75", alpha=0.6, fontweight="bold")
ax.text(bcg["market_share"].min(), bcg["growth"].max()*0.88, "Question Marks",
        fontsize=10, color="#378ADD", alpha=0.6, fontweight="bold")
ax.text(bcg["market_share"].min(), bcg["growth"].min()*1.1, "Dogs",
        fontsize=10, color="#888780", alpha=0.6, fontweight="bold")
ax.set_xlabel("Thị phần doanh thu 2025 (%)")
ax.set_ylabel("Tăng trưởng Q1/2026 so Q1/2025 (%)")
ax.set_title("Ma trận BCG — Phân loại 5 nhóm sản phẩm\nXe đạp Thống Nhất", pad=12)
_watermark(ax)
_save(fig, "03_bcg_matrix.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 04 — RFM Scatter  (Bubble chart)
# Lấy cảm hứng từ R1 + R3: RFM segmentation
# ══════════════════════════════════════════════════════════════════════════════
print("📊  Chart 04 — RFM Scatter...")
ref_date = fact["order_date"].max() + pd.Timedelta(days=1)
rfm = fact.groupby(["customer_code","customer_name"]).agg(
    last_order=("order_date","max"), freq=("so_number","nunique"),
    monetary  =("line_total","sum")
).reset_index()
rfm["recency"] = (ref_date - rfm["last_order"]).dt.days
rfm["R"] = pd.qcut(rfm["recency"], 5, labels=[5,4,3,2,1]).astype(int)
rfm["F"] = pd.qcut(rfm["freq"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
rfm["M"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
SEG_MAP = {(5,5):"Champions",(5,4):"Champions",(4,5):"Loyal",(4,4):"Loyal",
           (4,3):"Loyal",(3,5):"Có tiềm năng",(3,4):"Có tiềm năng",(5,3):"Mới gần đây",
           (2,5):"Nguy cơ rời bỏ",(2,4):"Nguy cơ rời bỏ",(2,3):"Nguy cơ rời bỏ",
           (1,5):"Không thể mất",(1,4):"Không thể mất",(2,2):"Ngủ đông",
           (1,3):"Ngủ đông",(1,2):"Đã mất",(1,1):"Đã mất"}
rfm["segment"]   = rfm.apply(lambda r: SEG_MAP.get((r.R, r.F), "Trung bình"), axis=1)
rfm["rfm_score"] = rfm["R"].astype(str) + rfm["F"].astype(str) + rfm["M"].astype(str)

fig, ax = plt.subplots(figsize=(12, 7))
for seg, grp in rfm.groupby("segment"):
    ax.scatter(grp["freq"], grp["recency"],
               s=grp["monetary"]/grp["monetary"].max()*600 + 20,
               c=SEG_C.get(seg, "#AAAAAA"), alpha=0.65, label=seg,
               edgecolors="white", linewidths=0.5)
ax.invert_yaxis()
ax.set_xlabel("Tần suất đặt hàng (số đơn)")
ax.set_ylabel("Recency — số ngày kể từ đơn cuối")
ax.set_title("Phân tích RFM — 622 đại lý Xe đạp Thống Nhất\n"
             "Kích thước bong bóng = Doanh thu tích lũy", pad=12)
handles, labels = ax.get_legend_handles_labels()
# Deduplicate
seen = {}
for h, l in zip(handles, labels):
    seen[l] = h
ax.legend(seen.values(), seen.keys(), loc="upper right",
          framealpha=0.85, ncol=2, fontsize=9)
_watermark(ax)
_save(fig, "04_rfm_scatter.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 05 — Top 20 tỉnh doanh thu  (Horizontal bar)
# Lấy cảm hứng từ R2: geographic revenue breakdown
# ══════════════════════════════════════════════════════════════════════════════
print("📊  Chart 05 — Top 20 tỉnh doanh thu...")
by_prov = (fact.groupby(["province_name","region"])["line_total"].sum()
           .reset_index().sort_values("line_total", ascending=False).head(20))

fig, ax = plt.subplots(figsize=(12, 8))
bars = ax.barh(by_prov["province_name"], by_prov["line_total"]/1e9,
               color=[RC.get(r, "#AAAAAA") for r in by_prov["region"]],
               edgecolor="white", linewidth=0.8, height=0.7)
for bar, val in zip(bars, by_prov["line_total"]):
    ax.text(bar.get_width()+0.02, bar.get_y()+bar.get_height()/2,
            f"{val/1e9:.1f} tỷ", va="center", fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("Doanh thu (tỷ đồng)")
ax.set_title("Top 20 tỉnh thành — Doanh thu tích lũy 2025–T2/2026", pad=12)
legend_patches = [mpatches.Patch(color=v, label=k) for k, v in RC.items()]
ax.legend(handles=legend_patches, loc="lower right", framealpha=0.85)
_watermark(ax)
_save(fig, "05_top20_tinh_doanh_thu.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 06 — Doanh thu 3 miền theo quý  (Stacked bar)
# Lấy cảm hứng từ R2: regional revenue by period
# ══════════════════════════════════════════════════════════════════════════════
print("📊  Chart 06 — Doanh thu 3 miền theo quý...")
by_reg = (fact.groupby(["fiscal_year","fiscal_quarter","region"])["line_total"]
          .sum().reset_index())
by_reg["q_label"] = by_reg.apply(
    lambda r: f"Q{int(r.fiscal_quarter)}/{str(int(r.fiscal_year))[2:]}", axis=1)
pivot = by_reg.pivot_table(index="q_label", columns="region",
                           values="line_total", fill_value=0)
# Sắp xếp theo thời gian
q_order = (by_reg.drop_duplicates("q_label")
           .sort_values(["fiscal_year","fiscal_quarter"])["q_label"].tolist())
pivot = pivot.reindex(q_order)

fig, ax = plt.subplots(figsize=(13, 6))
bottom = np.zeros(len(pivot))
for region in ["Miền Bắc", "Miền Trung", "Miền Nam"]:
    if region in pivot.columns:
        vals = pivot[region].values / 1e9
        bars = ax.bar(range(len(pivot)), vals, bottom=bottom,
                      label=region, color=RC[region],
                      edgecolor="white", linewidth=0.8)
        bottom += vals
for i, total in enumerate(bottom):
    ax.text(i, total + 0.1, f"{total:.1f}", ha="center", fontsize=9,
            fontweight="bold", color="#333333")
ax.set_xticks(range(len(pivot)))
ax.set_xticklabels(q_order, rotation=0)
ax.set_ylabel("Doanh thu (tỷ đồng)")
ax.set_title("Doanh thu theo vùng miền × Quý\nT1/2025 – T2/2026", pad=12)
ax.legend(loc="upper left", framealpha=0.85)
_watermark(ax)
_save(fig, "06_doanh_thu_3_mien_quy.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 07 — Heatmap màu sắc × nhóm sản phẩm
# Lấy cảm hứng từ R2: category-attribute matrix
# ══════════════════════════════════════════════════════════════════════════════
print("📊  Chart 07 — Heatmap màu sắc × nhóm SP...")
color_grp = (fact[fact["color"].notna() & (fact["color"]!="")]
             .groupby(["group_code","color"])["quantity"].sum().reset_index())
color_grp["group_label"] = color_grp["group_code"].map(GLABELS)
# Top 15 màu phổ biến nhất
top_colors = color_grp.groupby("color")["quantity"].sum().nlargest(15).index
color_grp = color_grp[color_grp["color"].isin(top_colors)]
pivot_c = color_grp.pivot_table(index="color", columns="group_label",
                                values="quantity", fill_value=0)

fig, ax = plt.subplots(figsize=(12, 7))
sns.heatmap(pivot_c, ax=ax, cmap="YlOrRd", annot=True, fmt=".0f",
            linewidths=0.5, linecolor="white",
            cbar_kws={"label": "Số lượng bán (chiếc)"})
ax.set_title("Phân tích màu sắc theo nhóm sản phẩm\nTop 15 màu phổ biến nhất", pad=12)
ax.set_xlabel(""); ax.set_ylabel("Màu sắc")
ax.tick_params(axis="x", rotation=25)
_save(fig, "07_heatmap_mau_nhom_sp.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 08 — Tăng trưởng doanh thu MoM  (Bar + Line combo)
# Lấy cảm hứng từ R2: MoM growth combo chart
# ══════════════════════════════════════════════════════════════════════════════
print("📊  Chart 08 — Tăng trưởng MoM...")
monthly_total = (fact.groupby(["fiscal_year","fiscal_month"])["line_total"]
                 .sum().reset_index().sort_values(["fiscal_year","fiscal_month"]))
monthly_total["ym"]      = monthly_total.apply(
    lambda r: f"T{int(r.fiscal_month)}/{str(int(r.fiscal_year))[2:]}", axis=1)
monthly_total["mom_pct"] = monthly_total["line_total"].pct_change() * 100

fig, ax1 = plt.subplots(figsize=(14, 6))
colors_bar = ["#1D9E75" if v >= 0 else "#E24B4A"
              for v in monthly_total["mom_pct"].fillna(0)]
ax1.bar(range(len(monthly_total)), monthly_total["line_total"]/1e9,
        color="#BDE4D5", edgecolor="white", linewidth=0.6, label="Doanh thu (tỷ)")
ax1.set_ylabel("Doanh thu (tỷ đồng)", color="#333333")
ax1.set_xticks(range(len(monthly_total)))
ax1.set_xticklabels(monthly_total["ym"].tolist(), rotation=45, ha="right")

ax2 = ax1.twinx()
ax2.plot(range(len(monthly_total)), monthly_total["mom_pct"],
         color="#1D9E75", linewidth=2.2, marker="o", markersize=5,
         label="Tăng trưởng MoM%", zorder=5)
ax2.axhline(0, color="#AAAAAA", linestyle="--", linewidth=0.8)
ax2.set_ylabel("Tăng trưởng MoM (%)", color="#1D9E75")
ax2.yaxis.label.set_color("#1D9E75")
ax2.tick_params(axis="y", colors="#1D9E75")
ax2.spines["right"].set_edgecolor("#1D9E75")

# Highlight tháng 3
for i, (_, row) in enumerate(monthly_total.iterrows()):
    if row.fiscal_month == 3:
        ax1.patches[i].set_facecolor("#1D9E75")
        ax1.patches[i].set_alpha(0.9)

fig.suptitle("Doanh thu và Tăng trưởng tháng (MoM)\nTháng 3 là đỉnh mùa vụ tựu trường",
             fontsize=14, fontweight="bold", y=1.01)
lines1, labs1 = ax1.get_legend_handles_labels()
lines2, labs2 = ax2.get_legend_handles_labels()
ax1.legend(lines1+lines2, labs1+labs2, loc="upper left", framealpha=0.85)
_save(fig, "08_tang_truong_mom.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 09 — Pareto đại lý  (Cumulative curve)
# Lấy cảm hứng từ R1: Pareto chart — top customers
# ══════════════════════════════════════════════════════════════════════════════
print("📊  Chart 09 — Pareto đại lý...")
by_dealer = fact.groupby("customer_code")["line_total"].sum().sort_values(ascending=False)
cumulative = (by_dealer.cumsum() / by_dealer.sum() * 100).values
n_dealers  = len(by_dealer)
x_pct      = np.arange(1, n_dealers+1) / n_dealers * 100

fig, ax1 = plt.subplots(figsize=(12, 6))
ax1.bar(range(n_dealers), by_dealer.values/1e6,
        color="#378ADD", alpha=0.6, width=1.0)
ax1.set_ylabel("Doanh thu đại lý (triệu đồng)", color="#378ADD")
ax1.set_xlabel(f"Xếp hạng đại lý (tổng {n_dealers} đại lý)")

ax2 = ax1.twinx()
ax2.plot(range(n_dealers), cumulative, color="#D85A30",
         linewidth=2.5, label="Tỷ trọng tích lũy (%)")
ax2.axhline(80, color="#AAAAAA", linestyle="--", linewidth=1)
ax2.set_ylabel("Tỷ trọng doanh thu tích lũy (%)", color="#D85A30")
ax2.yaxis.label.set_color("#D85A30")
ax2.tick_params(axis="y", colors="#D85A30")

# Điểm giao 80%
idx_80 = np.searchsorted(cumulative, 80)
ax2.annotate(f"Top {idx_80}/{n_dealers}\nchiếm 80% DT",
             xy=(idx_80, 80),
             xytext=(idx_80+30, 65),
             arrowprops=dict(arrowstyle="->", color="#D85A30"),
             color="#D85A30", fontweight="bold", fontsize=10)
ax1.set_title("Phân tích Pareto — Phân phối doanh thu theo đại lý\n"
              "Nguyên lý 80/20: thiểu số đại lý tạo đa số doanh thu", pad=12)
_save(fig, "09_pareto_dai_ly.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 10 — Phân khúc RFM  (Bar chart + KPI)
# Lấy cảm hứng từ R3 olist-churn: segment distribution
# ══════════════════════════════════════════════════════════════════════════════
print("📊  Chart 10 — Phân khúc RFM...")
seg_stats = (rfm.groupby("segment")
             .agg(so_dl=("customer_code","count"), tong_dt=("monetary","sum"))
             .reset_index().sort_values("tong_dt", ascending=False))
total_m = seg_stats["tong_dt"].sum()
seg_stats["dt_pct"] = seg_stats["tong_dt"] / total_m * 100

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))
colors_seg = [SEG_C.get(s, "#AAAAAA") for s in seg_stats["segment"]]

# Số đại lý
ax1.barh(seg_stats["segment"], seg_stats["so_dl"],
         color=colors_seg, edgecolor="white", linewidth=0.8, height=0.65)
for bar, v in zip(ax1.patches, seg_stats["so_dl"]):
    ax1.text(bar.get_width()+1, bar.get_y()+bar.get_height()/2,
             str(v), va="center", fontsize=10, fontweight="bold")
ax1.invert_yaxis()
ax1.set_xlabel("Số đại lý")
ax1.set_title("Số lượng đại lý\ntheo phân khúc RFM", fontsize=13, fontweight="bold")

# Doanh thu %
ax2.barh(seg_stats["segment"], seg_stats["dt_pct"],
         color=colors_seg, edgecolor="white", linewidth=0.8, height=0.65)
for bar, v in zip(ax2.patches, seg_stats["dt_pct"]):
    ax2.text(bar.get_width()+0.3, bar.get_y()+bar.get_height()/2,
             f"{v:.1f}%", va="center", fontsize=10, fontweight="bold")
ax2.invert_yaxis()
ax2.set_xlabel("% Doanh thu")
ax2.set_title("% Doanh thu đóng góp\ntheo phân khúc RFM", fontsize=13, fontweight="bold")
ax2.set_yticklabels([])

fig.suptitle("Phân tích RFM — Phân khúc 622 đại lý Xe đạp Thống Nhất",
             fontsize=14, fontweight="bold")
_save(fig, "10_rfm_segments.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 11 — So sánh Q1/2025 vs Q1/2026  (Grouped bar)
# Lấy cảm hứng từ R2: period comparison
# ══════════════════════════════════════════════════════════════════════════════
print("📊  Chart 11 — So sánh Q1/2025 vs Q1/2026...")
q1_25 = (fact[(fact.fiscal_year==2025)&(fact.fiscal_quarter==1)]
         .groupby("group_code")["line_total"].sum().reindex(GROUP_ORDER).fillna(0))
q1_26 = (fact[(fact.fiscal_year==2026)&(fact.fiscal_quarter==1)]
         .groupby("group_code")["line_total"].sum().reindex(GROUP_ORDER).fillna(0))
labels = [GLABELS[g] for g in GROUP_ORDER]
x      = np.arange(len(labels))
w      = 0.35

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10),
                                gridspec_kw={"height_ratios": [3, 1.5]})
b1 = ax1.bar(x-w/2, q1_25.values/1e9, w, label="Q1/2025",
             color="#AAAAAA", edgecolor="white", linewidth=0.8)
b2 = ax1.bar(x+w/2, q1_26.values/1e9, w, label="Q1/2026",
             color=[C[g] for g in GROUP_ORDER], edgecolor="white", linewidth=0.8)
for bar in [*b1, *b2]:
    h = bar.get_height()
    if h > 0:
        ax1.text(bar.get_x()+bar.get_width()/2, h+0.02,
                 f"{h:.1f}", ha="center", fontsize=9)
ax1.set_xticks(x); ax1.set_xticklabels(labels, rotation=15, ha="right")
ax1.set_ylabel("Doanh thu (tỷ đồng)")
ax1.set_title("So sánh doanh thu Q1/2025 và Q1/2026\ntheo nhóm sản phẩm", pad=12)
ax1.legend()

# YoY%
yoy = ((q1_26 - q1_25) / q1_25.replace(0, 1) * 100)
bar_colors = ["#1D9E75" if v >= 0 else "#E24B4A" for v in yoy.values]
bars = ax2.bar(x, yoy.values, color=bar_colors, edgecolor="white", linewidth=0.8)
ax2.axhline(0, color="#333333", linewidth=1)
for bar, v in zip(bars, yoy.values):
    va = "bottom" if v >= 0 else "top"
    offset = 0.5 if v >= 0 else -0.5
    ax2.text(bar.get_x()+bar.get_width()/2, v+offset,
             f"{v:+.1f}%", ha="center", va=va, fontsize=10, fontweight="bold",
             color="#333333")
ax2.set_xticks(x); ax2.set_xticklabels(labels, rotation=15, ha="right")
ax2.set_ylabel("Tăng trưởng YoY (%)")
ax2.set_title("Tốc độ tăng trưởng Q1 YoY (%)", fontsize=12, fontweight="bold")
_save(fig, "11_so_sanh_q1_2025_2026.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 12 — Top 20 SKU bán chạy nhất  (Horizontal bar)
# Lấy cảm hứng từ R1: top products analysis
# ══════════════════════════════════════════════════════════════════════════════
print("📊  Chart 12 — Top 20 SKU bán chạy nhất...")
by_sku = (fact.groupby(["product_code","product_name","color","group_code"])
          .agg(so_luong=("quantity","sum"), doanh_thu=("line_total","sum"))
          .reset_index().nlargest(20, "so_luong"))
by_sku["ten_ngan"] = by_sku["product_name"].str.replace("Xe đạp Thống Nhất ", "", regex=False)

fig, ax = plt.subplots(figsize=(12, 9))
bar_colors_sku = [C.get(g, "#AAAAAA") for g in by_sku["group_code"]]
bars = ax.barh(by_sku["ten_ngan"], by_sku["so_luong"],
               color=bar_colors_sku, edgecolor="white", linewidth=0.7, height=0.7)
for bar, sl, dt in zip(bars, by_sku["so_luong"], by_sku["doanh_thu"]):
    ax.text(bar.get_width()+2, bar.get_y()+bar.get_height()/2,
            f"{int(sl)} chiếc  ({dt/1e6:.0f}M)",
            va="center", fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("Số lượng bán (chiếc)")
ax.set_title("Top 20 SKU bán chạy nhất — T1/2025 – T2/2026\nXe đạp Thống Nhất", pad=12)
legend_patches = [mpatches.Patch(color=C[g], label=GLABELS[g]) for g in GROUP_ORDER if g in C]
ax.legend(handles=legend_patches, loc="lower right", framealpha=0.85)
_save(fig, "12_top20_sku.png")


# ══════════════════════════════════════════════════════════════════════════════
#  EXCEL — Bảng kết quả tổng hợp
# ══════════════════════════════════════════════════════════════════════════════
print("\n📋  Đang xuất bảng kết quả Excel...")
excel_path = TABLE_DIR / "tnbike_ketqua.xlsx"

with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:

    # Sheet 1: KPI tổng hợp
    kpi_rows = [
        ["CHỈ SỐ", "GIÁ TRỊ", "ĐƠN VỊ"],
        ["Tổng doanh thu",          fact["line_total"].sum(),         "VNĐ"],
        ["Tổng doanh thu",          fact["line_total"].sum()/1e9,     "Tỷ đồng"],
        ["Tổng đơn hàng",           fact["so_number"].nunique(),      "Đơn"],
        ["Tổng sản lượng",          int(fact["quantity"].sum()),      "Chiếc"],
        ["Tổng đại lý hoạt động",   fact["customer_code"].nunique(),  "Đại lý"],
        ["Giá bán trung bình",      fact["line_total"].sum()/fact["quantity"].sum(), "VNĐ/chiếc"],
        ["Doanh thu TB/đại lý",     fact["line_total"].sum()/fact["customer_code"].nunique(), "VNĐ"],
        ["Số tỉnh có doanh số",     fact["province_name"].dropna().nunique(), "Tỉnh/TP"],
        ["Tổng SKU được bán",       fact["product_code"].nunique(),   "SKU"],
    ]
    pd.DataFrame(kpi_rows[1:], columns=kpi_rows[0]).to_excel(
        writer, sheet_name="1. KPI Tổng hợp", index=False)

    # Sheet 2: Doanh thu theo tháng × nhóm SP
    dt_monthly = (fact.groupby(["fiscal_year","fiscal_month","group_code","group_name"])
                  .agg(doanh_thu=("line_total","sum"), so_luong=("quantity","sum"),
                       so_don=("so_number","nunique")).reset_index())
    dt_monthly["ym"] = dt_monthly.apply(lambda r: f"T{int(r.fiscal_month)}/{int(r.fiscal_year)}", axis=1)
    dt_monthly.to_excel(writer, sheet_name="2. DT Tháng × Nhóm SP", index=False)

    # Sheet 3: RFM đại lý
    rfm_out = rfm[["customer_code","customer_name","recency","freq","monetary","R","F","M","rfm_score","segment"]].copy()
    rfm_out.columns = ["Mã đại lý","Tên đại lý","Recency (ngày)","Tần suất","Doanh thu","R","F","M","RFM Score","Phân khúc"]
    rfm_out = rfm_out.sort_values("Doanh thu", ascending=False)
    rfm_out.to_excel(writer, sheet_name="3. RFM Đại lý", index=False)

    # Sheet 4: Doanh thu theo tỉnh
    prov_out = (fact.groupby(["province_name","region"])
                .agg(doanh_thu=("line_total","sum"),
                     so_luong=("quantity","sum"),
                     so_don=("so_number","nunique"),
                     so_dai_ly=("customer_code","nunique"))
                .reset_index().sort_values("doanh_thu", ascending=False))
    prov_out.columns = ["Tỉnh/Thành phố","Vùng miền","Doanh thu (VNĐ)","Số lượng","Số đơn","Số đại lý"]
    prov_out.to_excel(writer, sheet_name="4. DT Tỉnh Thành", index=False)

    # Sheet 5: BCG Matrix
    bcg_out = bcg[["market_share","growth","label"]].reset_index()
    bcg_out.columns = ["Nhóm SP","Thị phần 2025 (%)","Tăng trưởng Q1 YoY (%)","BCG Label"]
    bcg_out["Tên nhóm"] = bcg_out["Nhóm SP"].map(GLABELS)
    bcg_out.to_excel(writer, sheet_name="5. BCG Matrix", index=False)

    # Sheet 6: Top 50 SKU
    top_sku = (fact.groupby(["product_code","product_name","color","group_code","group_name"])
               .agg(so_luong=("quantity","sum"), doanh_thu=("line_total","sum"),
                    gia_tb=("unit_price","mean"), so_don=("so_number","nunique"))
               .reset_index().nlargest(50, "doanh_thu"))
    top_sku.columns = ["Mã hàng","Tên sản phẩm","Màu sắc","Nhóm SP","Tên nhóm",
                        "Số lượng","Doanh thu (VNĐ)","Giá TB","Số đơn"]
    top_sku.to_excel(writer, sheet_name="6. Top 50 SKU", index=False)

    # Sheet 7: Tăng trưởng tỉnh Q1 YoY
    q1_25_p = fact[(fact.fiscal_year==2025)&(fact.fiscal_quarter==1)].groupby("province_name")["line_total"].sum()
    q1_26_p = fact[(fact.fiscal_year==2026)&(fact.fiscal_quarter==1)].groupby("province_name")["line_total"].sum()
    growth_p = pd.DataFrame({"Q1/2025": q1_25_p, "Q1/2026": q1_26_p}).fillna(0)
    growth_p["Tăng trưởng YoY (%)"] = ((growth_p["Q1/2026"]-growth_p["Q1/2025"])
                                         /growth_p["Q1/2025"].replace(0,1)*100).round(1)
    growth_p = growth_p.reset_index().sort_values("Tăng trưởng YoY (%)", ascending=False)
    growth_p.columns = ["Tỉnh/TP","DT Q1/2025","DT Q1/2026","Tăng trưởng YoY (%)"]
    growth_p.to_excel(writer, sheet_name="7. Tăng trưởng Tỉnh Q1", index=False)

print(f"  ✓ {excel_path}")

# ══════════════════════════════════════════════════════════════════════════════
#  TỔNG KẾT
# ══════════════════════════════════════════════════════════════════════════════
print(f"""
{'='*58}
✅  HOÀN THÀNH!
{'='*58}
📁  Charts  ({CHART_DIR}):
    01_doanh_thu_theo_thang.png
    02_co_cau_nhom_sp.png
    03_bcg_matrix.png
    04_rfm_scatter.png
    05_top20_tinh_doanh_thu.png
    06_doanh_thu_3_mien_quy.png
    07_heatmap_mau_nhom_sp.png
    08_tang_truong_mom.png
    09_pareto_dai_ly.png
    10_rfm_segments.png
    11_so_sanh_q1_2025_2026.png
    12_top20_sku.png

📊  Excel  ({TABLE_DIR}/tnbike_ketqua.xlsx):
    Sheet 1: KPI Tổng hợp
    Sheet 2: DT Tháng × Nhóm SP
    Sheet 3: RFM 622 Đại lý
    Sheet 4: DT 63 Tỉnh Thành
    Sheet 5: BCG Matrix
    Sheet 6: Top 50 SKU
    Sheet 7: Tăng trưởng Tỉnh Q1
{'='*58}
""")
