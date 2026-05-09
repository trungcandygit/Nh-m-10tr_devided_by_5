"""
Xuất toàn bộ kết quả phân tích thành CSV — siêu chi tiết
Chạy: python export_csv.py
Output: output/csv/ (40+ file)
"""
import warnings, logging, sys, os
warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
from pathlib import Path
from analytics.sql_data_loader import load_all, build_fact

OUT = Path("output/csv")
OUT.mkdir(parents=True, exist_ok=True)

def save(df, name):
    p = OUT / name
    df.to_csv(p, index=False, encoding="utf-8-sig")
    print(f"  ✓ {name:<55} {len(df):>6,} dòng")
    return df

print("⏳ Tải dữ liệu...")
dfs  = load_all()
fact = build_fact(dfs)
fact["order_date"] = pd.to_datetime(fact["order_date"])
fact["ym"]  = fact["fiscal_year"].astype(str) + "-" + fact["fiscal_month"].astype(str).str.zfill(2)
fact["week"] = fact["order_date"].dt.isocalendar().week.astype(int)
fact["dow"]  = fact["order_date"].dt.day_name()
fact["dom"]  = fact["order_date"].dt.day
print(f"  → {len(fact):,} dòng × {fact.shape[1]} cột\n")
print("📂 Đang xuất CSV...\n")

# ─────────────────────────────────────────────────────────────────────────────
# NHÓM 1 — RAW / MASTER DATA
# ─────────────────────────────────────────────────────────────────────────────
print("── Nhóm 1: Raw / Master ──")

# 01
save(fact[[
    "so_number","order_date","fiscal_year","fiscal_month","fiscal_quarter","week",
    "customer_code","customer_name","province_name","region",
    "product_code","product_name","color","line_name","group_code","group_name",
    "quantity","unit_price","line_total"
]].sort_values(["order_date","so_number"]), "01_fact_sales_full.csv")

# 02 — danh sách đơn hàng (header)
orders = (fact.groupby(["so_number","order_date","fiscal_year","fiscal_month",
                         "fiscal_quarter","customer_code","customer_name",
                         "province_name","region"])
          .agg(tong_dong=("product_code","count"),
               tong_sl=("quantity","sum"),
               tong_tien=("line_total","sum"),
               so_nhom_sp=("group_code","nunique"),
               so_sku=("product_code","nunique"))
          .reset_index().sort_values("order_date"))
save(orders, "02_sales_orders_header.csv")

# 03 — danh sách khách hàng + thống kê
cus_stats = (fact.groupby(["customer_code","customer_name","province_name","region"])
             .agg(so_don=("so_number","nunique"),
                  tong_sl=("quantity","sum"),
                  tong_dt=("line_total","sum"),
                  ngay_dau=("order_date","min"),
                  ngay_cuoi=("order_date","max"),
                  so_nhom_sp=("group_code","nunique"),
                  so_sku=("product_code","nunique"))
             .reset_index())
cus_stats["gia_tb_chiec"] = (cus_stats["tong_dt"] / cus_stats["tong_sl"]).round(0)
cus_stats["span_ngay"] = (cus_stats["ngay_cuoi"] - cus_stats["ngay_dau"]).dt.days
cus_stats["don_tb_gia_tri"] = (cus_stats["tong_dt"] / cus_stats["so_don"]).round(0)
save(cus_stats.sort_values("tong_dt", ascending=False), "03_customers_stats.csv")

# 04 — danh sách sản phẩm + thống kê
prod_stats = (fact.groupby(["product_code","product_name","color","line_name","group_code","group_name"])
              .agg(so_don=("so_number","nunique"),
                   tong_sl=("quantity","sum"),
                   tong_dt=("line_total","sum"),
                   gia_min=("unit_price","min"),
                   gia_max=("unit_price","max"),
                   gia_tb=("unit_price","mean"),
                   so_dai_ly=("customer_code","nunique"),
                   so_tinh=("province_name","nunique"))
              .reset_index())
prod_stats["dt_per_don"] = (prod_stats["tong_dt"] / prod_stats["so_don"]).round(0)
save(prod_stats.sort_values("tong_dt", ascending=False), "04_products_stats.csv")

# 05 — tỉnh thành chi tiết
prov_stats = (fact.groupby(["province_name","region"])
              .agg(so_dai_ly=("customer_code","nunique"),
                   so_don=("so_number","nunique"),
                   tong_sl=("quantity","sum"),
                   tong_dt=("line_total","sum"),
                   so_sku=("product_code","nunique"),
                   so_nhom_sp=("group_code","nunique"),
                   ngay_dau=("order_date","min"),
                   ngay_cuoi=("order_date","max"))
              .reset_index())
prov_stats["dt_tb_dai_ly"] = (prov_stats["tong_dt"] / prov_stats["so_dai_ly"]).round(0)
prov_stats["dt_tb_don"]    = (prov_stats["tong_dt"] / prov_stats["so_don"]).round(0)
prov_stats["rank_dt"] = prov_stats["tong_dt"].rank(ascending=False).astype(int)
save(prov_stats.sort_values("tong_dt", ascending=False), "05_provinces_stats.csv")

# ─────────────────────────────────────────────────────────────────────────────
# NHÓM 2 — THỜI GIAN
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Nhóm 2: Thời gian ──")

# 06 — theo ngày
daily = (fact.groupby(["order_date","fiscal_year","fiscal_month","fiscal_quarter","week","dow","dom"])
         .agg(so_don=("so_number","nunique"),
              tong_sl=("quantity","sum"),
              tong_dt=("line_total","sum"),
              so_dai_ly=("customer_code","nunique"),
              so_sku=("product_code","nunique"))
         .reset_index().sort_values("order_date"))
daily["dt_tb_don"] = (daily["tong_dt"] / daily["so_don"]).round(0)
save(daily, "06_daily_revenue.csv")

# 07 — theo tuần
weekly = (fact.groupby(["fiscal_year","week"])
          .agg(so_don=("so_number","nunique"),
               tong_sl=("quantity","sum"),
               tong_dt=("line_total","sum"),
               so_dai_ly=("customer_code","nunique"))
          .reset_index().sort_values(["fiscal_year","week"]))
weekly["mom_pct"] = weekly["tong_dt"].pct_change().mul(100).round(1)
save(weekly, "07_weekly_revenue.csv")

# 08 — theo tháng tổng
monthly = (fact.groupby(["fiscal_year","fiscal_month","ym"])
           .agg(so_don=("so_number","nunique"),
                tong_sl=("quantity","sum"),
                tong_dt=("line_total","sum"),
                so_dai_ly=("customer_code","nunique"),
                so_sku=("product_code","nunique"),
                so_tinh=("province_name","nunique"))
           .reset_index().sort_values(["fiscal_year","fiscal_month"]))
monthly["mom_pct"]      = monthly["tong_dt"].pct_change().mul(100).round(1)
monthly["sl_mom_pct"]   = monthly["tong_sl"].pct_change().mul(100).round(1)
monthly["don_mom_pct"]  = monthly["so_don"].pct_change().mul(100).round(1)
monthly["dt_tb_don"]    = (monthly["tong_dt"] / monthly["so_don"]).round(0)
monthly["dt_tb_dai_ly"] = (monthly["tong_dt"] / monthly["so_dai_ly"]).round(0)
save(monthly, "08_monthly_revenue.csv")

# 09 — theo tháng × nhóm SP
monthly_grp = (fact.groupby(["fiscal_year","fiscal_month","ym","group_code","group_name"])
               .agg(so_don=("so_number","nunique"),
                    tong_sl=("quantity","sum"),
                    tong_dt=("line_total","sum"),
                    so_dai_ly=("customer_code","nunique"))
               .reset_index().sort_values(["fiscal_year","fiscal_month","group_code"]))
total_by_month = monthly_grp.groupby("ym")["tong_dt"].transform("sum")
monthly_grp["ty_trong_pct"] = (monthly_grp["tong_dt"] / total_by_month * 100).round(2)
save(monthly_grp, "09_monthly_by_group.csv")

# 10 — theo quý tổng
quarterly = (fact.groupby(["fiscal_year","fiscal_quarter"])
             .agg(so_don=("so_number","nunique"),
                  tong_sl=("quantity","sum"),
                  tong_dt=("line_total","sum"),
                  so_dai_ly=("customer_code","nunique"),
                  so_sku=("product_code","nunique"))
             .reset_index().sort_values(["fiscal_year","fiscal_quarter"]))
quarterly["q_label"] = "Q" + quarterly["fiscal_quarter"].astype(str) + "/" + quarterly["fiscal_year"].astype(str)
quarterly["qoq_pct"] = quarterly["tong_dt"].pct_change().mul(100).round(1)
save(quarterly, "10_quarterly_revenue.csv")

# 11 — theo quý × nhóm SP
quarterly_grp = (fact.groupby(["fiscal_year","fiscal_quarter","group_code","group_name"])
                 .agg(so_don=("so_number","nunique"),
                      tong_sl=("quantity","sum"),
                      tong_dt=("line_total","sum"))
                 .reset_index())
quarterly_grp["q_label"] = "Q" + quarterly_grp["fiscal_quarter"].astype(str) + "/" + quarterly_grp["fiscal_year"].astype(str)
save(quarterly_grp, "11_quarterly_by_group.csv")

# 12 — pivot tháng × nhóm (wide format cho chart)
pivot_monthly = (fact.groupby(["ym","group_code"])["line_total"]
                 .sum().unstack(fill_value=0).reset_index())
pivot_monthly["TONG"] = pivot_monthly.iloc[:,1:].sum(axis=1)
save(pivot_monthly, "12_pivot_month_x_group.csv")

# 13 — theo ngày trong tuần (seasonality)
dow_stats = (fact.groupby("dow")
             .agg(so_don=("so_number","nunique"),
                  tong_sl=("quantity","sum"),
                  tong_dt=("line_total","sum"))
             .reset_index())
dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
dow_stats["dow_order"] = dow_stats["dow"].map({d:i for i,d in enumerate(dow_order)})
save(dow_stats.sort_values("dow_order").drop("dow_order",axis=1), "13_day_of_week_pattern.csv")

# 14 — theo ngày trong tháng
dom_stats = (fact.groupby("dom")
             .agg(so_don=("so_number","nunique"),
                  tong_sl=("quantity","sum"),
                  tong_dt=("line_total","sum"))
             .reset_index().sort_values("dom"))
save(dom_stats, "14_day_of_month_pattern.csv")

# ─────────────────────────────────────────────────────────────────────────────
# NHÓM 3 — SẢN PHẨM
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Nhóm 3: Sản phẩm ──")

# 15 — nhóm SP tổng
grp_total = (fact.groupby(["group_code","group_name"])
             .agg(so_don=("so_number","nunique"),
                  tong_sl=("quantity","sum"),
                  tong_dt=("line_total","sum"),
                  so_dai_ly=("customer_code","nunique"),
                  so_sku=("product_code","nunique"),
                  so_tinh=("province_name","nunique"),
                  gia_tb=("unit_price","mean"),
                  gia_min=("unit_price","min"),
                  gia_max=("unit_price","max"))
             .reset_index())
grp_total["ty_trong_pct"] = (grp_total["tong_dt"] / grp_total["tong_dt"].sum() * 100).round(2)
grp_total["ty_trong_sl_pct"] = (grp_total["tong_sl"] / grp_total["tong_sl"].sum() * 100).round(2)
save(grp_total.sort_values("tong_dt", ascending=False), "15_group_summary.csv")

# 16 — dòng xe (product line)
line_stats = (fact.groupby(["line_id","line_name","group_code","group_name"])
              .agg(so_don=("so_number","nunique"),
                   tong_sl=("quantity","sum"),
                   tong_dt=("line_total","sum"),
                   so_sku=("product_code","nunique"),
                   so_dai_ly=("customer_code","nunique"),
                   gia_tb=("unit_price","mean"))
              .reset_index())
line_stats["ty_trong_nhom"] = (line_stats.groupby("group_code")["tong_dt"]
                                .transform(lambda x: x / x.sum() * 100)).round(2)
save(line_stats.sort_values("tong_dt", ascending=False), "16_product_line_stats.csv")

# 17 — top 50 SKU
top_sku = prod_stats.nlargest(50, "tong_dt").reset_index(drop=True)
top_sku["rank"] = range(1, 51)
top_sku["ty_trong_pct"] = (top_sku["tong_dt"] / fact["line_total"].sum() * 100).round(3)
save(top_sku, "17_top50_sku.csv")

# 18 — tất cả SKU xếp hạng
all_sku_rank = prod_stats.sort_values("tong_dt", ascending=False).reset_index(drop=True)
all_sku_rank["rank"] = range(1, len(all_sku_rank)+1)
all_sku_rank["cumulative_pct"] = (all_sku_rank["tong_dt"].cumsum()
                                   / all_sku_rank["tong_dt"].sum() * 100).round(2)
all_sku_rank["abc"] = pd.cut(all_sku_rank["cumulative_pct"],
                              bins=[0,70,90,100], labels=["A","B","C"])
save(all_sku_rank, "18_sku_abc_ranking.csv")

# 19 — màu sắc × nhóm SP
color_grp = (fact[fact["color"].notna() & (fact["color"]!="")]
             .groupby(["group_code","group_name","color"])
             .agg(so_don=("so_number","nunique"),
                  tong_sl=("quantity","sum"),
                  tong_dt=("line_total","sum"),
                  so_sku=("product_code","nunique"))
             .reset_index())
color_grp["ty_trong_nhom_pct"] = (color_grp.groupby("group_code")["tong_sl"]
                                   .transform(lambda x: x/x.sum()*100)).round(2)
save(color_grp.sort_values(["group_code","tong_sl"], ascending=[True,False]),
     "19_color_by_group.csv")

# 20 — màu sắc × tháng × nhóm
color_monthly = (fact[fact["color"].notna() & (fact["color"]!="")]
                 .groupby(["fiscal_year","fiscal_month","ym","group_code","color"])
                 .agg(tong_sl=("quantity","sum"),
                      tong_dt=("line_total","sum"))
                 .reset_index().sort_values(["ym","group_code","tong_sl"], ascending=[True,True,False]))
save(color_monthly, "20_color_monthly_trend.csv")

# 21 — pivot màu sắc (wide: màu là cột)
pivot_color = (fact[fact["color"].notna() & (fact["color"]!="")]
               .groupby(["group_code","color"])["quantity"]
               .sum().unstack(fill_value=0).reset_index())
save(pivot_color, "21_pivot_color_x_group.csv")

# 22 — SKU theo tháng (top 30 SKU)
top30_codes = prod_stats.nlargest(30,"tong_dt")["product_code"].tolist()
sku_monthly = (fact[fact["product_code"].isin(top30_codes)]
               .groupby(["product_code","product_name","color","group_code",
                          "fiscal_year","fiscal_month","ym"])
               .agg(tong_sl=("quantity","sum"),
                    tong_dt=("line_total","sum"))
               .reset_index().sort_values(["product_code","ym"]))
save(sku_monthly, "22_top30_sku_monthly.csv")

# 23 — phân tích giá theo nhóm
price_analysis = (fact.groupby(["group_code","group_name","fiscal_year","fiscal_month"])
                  .agg(gia_min=("unit_price","min"),
                       gia_max=("unit_price","max"),
                       gia_tb=("unit_price","mean"),
                       gia_median=("unit_price","median"),
                       gia_std=("unit_price","std"))
                  .reset_index())
price_analysis["gia_range"] = price_analysis["gia_max"] - price_analysis["gia_min"]
save(price_analysis.sort_values(["group_code","fiscal_year","fiscal_month"]),
     "23_price_analysis_by_group_month.csv")

# 24 — dòng xe × tháng
line_monthly = (fact.groupby(["line_name","group_code","fiscal_year","fiscal_month","ym"])
                .agg(tong_sl=("quantity","sum"),
                     tong_dt=("line_total","sum"),
                     so_don=("so_number","nunique"))
                .reset_index().sort_values(["line_name","ym"]))
save(line_monthly, "24_product_line_monthly.csv")

# ─────────────────────────────────────────────────────────────────────────────
# NHÓM 4 — ĐỊA LÝ
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Nhóm 4: Địa lý ──")

# 25 — tỉnh × tháng
prov_monthly = (fact.groupby(["province_name","region","fiscal_year","fiscal_month","ym"])
                .agg(so_don=("so_number","nunique"),
                     tong_sl=("quantity","sum"),
                     tong_dt=("line_total","sum"),
                     so_dai_ly=("customer_code","nunique"))
                .reset_index().sort_values(["province_name","ym"]))
prov_monthly["dt_tb_dai_ly"] = (prov_monthly["tong_dt"] / prov_monthly["so_dai_ly"]).round(0)
save(prov_monthly, "25_province_monthly.csv")

# 26 — tỉnh × quý
prov_quarterly = (fact.groupby(["province_name","region","fiscal_year","fiscal_quarter"])
                  .agg(so_don=("so_number","nunique"),
                       tong_sl=("quantity","sum"),
                       tong_dt=("line_total","sum"),
                       so_dai_ly=("customer_code","nunique"))
                  .reset_index())
prov_quarterly["q_label"] = ("Q" + prov_quarterly["fiscal_quarter"].astype(str)
                              + "/" + prov_quarterly["fiscal_year"].astype(str))
save(prov_quarterly, "26_province_quarterly.csv")

# 27 — tỉnh × nhóm SP
prov_grp = (fact.groupby(["province_name","region","group_code","group_name"])
            .agg(tong_sl=("quantity","sum"),
                 tong_dt=("line_total","sum"),
                 so_don=("so_number","nunique"),
                 so_dai_ly=("customer_code","nunique"))
            .reset_index().sort_values(["province_name","tong_dt"], ascending=[True,False]))
save(prov_grp, "27_province_by_group.csv")

# 28 — vùng miền × quý
region_qtr = (fact.groupby(["region","fiscal_year","fiscal_quarter"])
              .agg(so_don=("so_number","nunique"),
                   tong_sl=("quantity","sum"),
                   tong_dt=("line_total","sum"),
                   so_dai_ly=("customer_code","nunique"),
                   so_tinh=("province_name","nunique"))
              .reset_index())
region_qtr["q_label"] = "Q" + region_qtr["fiscal_quarter"].astype(str) + "/" + region_qtr["fiscal_year"].astype(str)
save(region_qtr.sort_values(["region","fiscal_year","fiscal_quarter"]), "28_region_quarterly.csv")

# 29 — vùng miền × tháng × nhóm SP
region_monthly_grp = (fact.groupby(["region","fiscal_year","fiscal_month","ym","group_code"])
                      .agg(tong_dt=("line_total","sum"),
                           tong_sl=("quantity","sum"))
                      .reset_index().sort_values(["region","ym"]))
save(region_monthly_grp, "29_region_monthly_by_group.csv")

# 30 — tăng trưởng YoY tỉnh (Q1/2025 vs Q1/2026)
q1_25_p = (fact[(fact.fiscal_year==2025) & (fact.fiscal_quarter==1)]
           .groupby("province_name")["line_total"].sum().rename("q1_2025"))
q1_26_p = (fact[(fact.fiscal_year==2026) & (fact.fiscal_quarter==1)]
           .groupby("province_name")["line_total"].sum().rename("q1_2026"))
prov_yoy = pd.concat([q1_25_p, q1_26_p], axis=1).fillna(0).reset_index()
prov_yoy["yoy_pct"] = ((prov_yoy["q1_2026"] - prov_yoy["q1_2025"])
                        / prov_yoy["q1_2025"].replace(0,1) * 100).round(1)
prov_yoy["tang_tuyet_doi"] = (prov_yoy["q1_2026"] - prov_yoy["q1_2025"]).round(0)
prov_yoy = prov_yoy.merge(fact[["province_name","region"]].drop_duplicates(), on="province_name", how="left")
save(prov_yoy.sort_values("yoy_pct", ascending=False), "30_province_yoy_growth.csv")

# 31 — pivot tỉnh × nhóm SP (wide)
pivot_prov_grp = (fact.groupby(["province_name","group_code"])["line_total"]
                  .sum().unstack(fill_value=0).reset_index())
pivot_prov_grp["TONG"] = pivot_prov_grp.iloc[:,1:].sum(axis=1)
save(pivot_prov_grp.sort_values("TONG", ascending=False), "31_pivot_province_x_group.csv")

# ─────────────────────────────────────────────────────────────────────────────
# NHÓM 5 — ĐẠI LÝ / KHÁCH HÀNG
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Nhóm 5: Đại lý / Khách hàng ──")

# 32 — RFM đầy đủ
ref_date = fact["order_date"].max() + pd.Timedelta(days=1)
rfm = fact.groupby(["customer_code","customer_name","province_name","region"]).agg(
    ngay_dau=("order_date","min"),
    ngay_cuoi=("order_date","max"),
    so_don=("so_number","nunique"),
    tong_sl=("quantity","sum"),
    tong_dt=("line_total","sum"),
    so_nhom_sp=("group_code","nunique"),
    so_sku=("product_code","nunique"),
    don_tb_sl=("quantity","mean"),
    don_tb_tien=("line_total","mean"),
).reset_index()
rfm["recency"]  = (ref_date - rfm["ngay_cuoi"]).dt.days
rfm["lifespan"] = (rfm["ngay_cuoi"] - rfm["ngay_dau"]).dt.days
rfm["R"] = pd.qcut(rfm["recency"], 5, labels=[5,4,3,2,1]).astype(int)
rfm["F"] = pd.qcut(rfm["so_don"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
rfm["M"] = pd.qcut(rfm["tong_dt"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
rfm["rfm_score"]  = rfm["R"].astype(str) + rfm["F"].astype(str) + rfm["M"].astype(str)
rfm["rfm_sum"]    = rfm["R"] + rfm["F"] + rfm["M"]
SEG = {(5,5):"Champions",(5,4):"Champions",(4,5):"Loyal",(4,4):"Loyal",
       (4,3):"Loyal",(3,5):"Có tiềm năng",(3,4):"Có tiềm năng",
       (5,3):"Mới gần đây",(2,5):"Nguy cơ rời bỏ",(2,4):"Nguy cơ rời bỏ",
       (2,3):"Nguy cơ rời bỏ",(1,5):"Không thể mất",(1,4):"Không thể mất",
       (2,2):"Ngủ đông",(1,3):"Ngủ đông",(1,2):"Đã mất",(1,1):"Đã mất"}
rfm["segment"] = rfm.apply(lambda r: SEG.get((r.R, r.F), "Trung bình"), axis=1)
rfm["clv_est"]  = (rfm["tong_dt"] / rfm["lifespan"].replace(0,1) * 365).round(0)
rfm["dt_tb_don"] = (rfm["tong_dt"] / rfm["so_don"]).round(0)
rfm["rank_dt"]   = rfm["tong_dt"].rank(ascending=False).astype(int)
rfm["cumul_pct"] = (rfm.sort_values("tong_dt",ascending=False)["tong_dt"]
                    .cumsum() / rfm["tong_dt"].sum() * 100).round(2)
save(rfm.sort_values("tong_dt", ascending=False), "32_rfm_full.csv")

# 33 — phân khúc RFM tổng hợp
seg_summary = (rfm.groupby("segment")
               .agg(so_dai_ly=("customer_code","count"),
                    tong_dt=("tong_dt","sum"),
                    tong_sl=("tong_sl","sum"),
                    dt_tb=("tong_dt","mean"),
                    recency_tb=("recency","mean"),
                    so_don_tb=("so_don","mean"),
                    clv_tb=("clv_est","mean"))
               .reset_index())
seg_summary["ty_trong_dai_ly_pct"] = (seg_summary["so_dai_ly"]/seg_summary["so_dai_ly"].sum()*100).round(1)
seg_summary["ty_trong_dt_pct"]     = (seg_summary["tong_dt"]/seg_summary["tong_dt"].sum()*100).round(2)
save(seg_summary.sort_values("tong_dt",ascending=False), "33_rfm_segment_summary.csv")

# 34 — đại lý × tháng (cross-sell pattern)
cus_monthly = (fact.groupby(["customer_code","customer_name","fiscal_year","fiscal_month","ym"])
               .agg(so_don=("so_number","nunique"),
                    tong_sl=("quantity","sum"),
                    tong_dt=("line_total","sum"),
                    so_nhom_sp=("group_code","nunique"),
                    so_sku=("product_code","nunique"))
               .reset_index().sort_values(["customer_code","ym"]))
save(cus_monthly, "34_customer_monthly.csv")

# 35 — đại lý × nhóm SP
cus_grp = (fact.groupby(["customer_code","customer_name","group_code","group_name"])
           .agg(tong_sl=("quantity","sum"),
                tong_dt=("line_total","sum"),
                so_don=("so_number","nunique"))
           .reset_index())
cus_grp["ty_trong_kh_pct"] = (cus_grp.groupby("customer_code")["tong_dt"]
                               .transform(lambda x: x/x.sum()*100)).round(2)
save(cus_grp.sort_values(["customer_code","tong_dt"], ascending=[True,False]),
     "35_customer_by_group.csv")

# 36 — Pareto đại lý
pareto = rfm[["customer_code","customer_name","province_name","region",
              "segment","tong_dt","so_don","recency","rank_dt"]].copy()
pareto = pareto.sort_values("tong_dt", ascending=False).reset_index(drop=True)
pareto["cumul_dt"] = pareto["tong_dt"].cumsum()
pareto["cumul_pct"] = (pareto["cumul_dt"] / pareto["tong_dt"].sum() * 100).round(2)
pareto["pareto_group"] = pd.cut(pareto["cumul_pct"], bins=[0,50,80,95,100],
                                 labels=["Top 50%","50-80%","80-95%","Bottom 5%"])
save(pareto, "36_pareto_dealers.csv")

# 37 — đại lý mới vs cũ (cohort tháng đầu tiên mua)
rfm_cohort = rfm[["customer_code","customer_name","province_name","region","ngay_dau",
                   "tong_dt","so_don","segment"]].copy()
rfm_cohort["cohort_month"] = rfm_cohort["ngay_dau"].dt.to_period("M").astype(str)
rfm_cohort["cohort_year"]  = rfm_cohort["ngay_dau"].dt.year
save(rfm_cohort.sort_values("ngay_dau"), "37_customer_cohort.csv")

# 38 — cohort monthly summary
cohort_sum = (rfm_cohort.groupby("cohort_month")
              .agg(so_dai_ly_moi=("customer_code","count"),
                   tong_dt=("tong_dt","sum"),
                   dt_tb=("tong_dt","mean"))
              .reset_index().sort_values("cohort_month"))
save(cohort_sum, "38_cohort_summary.csv")

# 39 — basket size analysis
basket = (fact.groupby("so_number")
          .agg(so_dong=("product_code","count"),
               so_sku_khac_nhau=("product_code","nunique"),
               so_nhom_sp=("group_code","nunique"),
               tong_sl=("quantity","sum"),
               tong_tien=("line_total","sum"),
               ngay_dat=("order_date","first"),
               ma_dai_ly=("customer_code","first"))
          .reset_index())
basket["aov"]         = (basket["tong_tien"] / basket["so_dong"]).round(0)
basket["ym"]          = basket["ngay_dat"].dt.to_period("M").astype(str)
basket["is_cross_sell"] = (basket["so_nhom_sp"] > 1).astype(int)
save(basket.sort_values("tong_tien", ascending=False), "39_basket_analysis.csv")

# 40 — basket summary theo tháng
basket_monthly = (basket.groupby("ym")
                  .agg(so_don=("so_number","count"),
                       aov_tb=("tong_tien","mean"),
                       sl_tb_don=("tong_sl","mean"),
                       dong_tb_don=("so_dong","mean"),
                       ty_le_cross_sell=("is_cross_sell","mean"))
                  .reset_index())
basket_monthly["ty_le_cross_sell"] = (basket_monthly["ty_le_cross_sell"]*100).round(1)
save(basket_monthly, "40_basket_monthly_summary.csv")

# ─────────────────────────────────────────────────────────────────────────────
# NHÓM 6 — BCG + SO SÁNH
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Nhóm 6: BCG & So sánh ──")

# 41 — BCG chi tiết
rev_2025    = fact[fact.fiscal_year==2025].groupby("group_code")["line_total"].sum()
rev_q1_25   = fact[(fact.fiscal_year==2025)&(fact.fiscal_quarter==1)].groupby("group_code")["line_total"].sum()
rev_q1_26   = fact[(fact.fiscal_year==2026)&(fact.fiscal_quarter==1)].groupby("group_code")["line_total"].sum()
sl_2025     = fact[fact.fiscal_year==2025].groupby("group_code")["quantity"].sum()
sl_q1_26    = fact[(fact.fiscal_year==2026)&(fact.fiscal_quarter==1)].groupby("group_code")["quantity"].sum()
bcg_df = pd.DataFrame({
    "rev_2025": rev_2025, "rev_q1_2025": rev_q1_25, "rev_q1_2026": rev_q1_26,
    "sl_2025": sl_2025,   "sl_q1_2026":  sl_q1_26
}).fillna(0)
bcg_df["market_share_pct"] = (bcg_df["rev_2025"] / bcg_df["rev_2025"].sum() * 100).round(2)
bcg_df["sl_share_pct"]     = (bcg_df["sl_2025"]  / bcg_df["sl_2025"].sum()  * 100).round(2)
bcg_df["yoy_pct"]          = ((bcg_df["rev_q1_2026"] - bcg_df["rev_q1_2025"])
                               / bcg_df["rev_q1_2025"].replace(0,1) * 100).round(1)
med_s = bcg_df["market_share_pct"].median()
med_g = bcg_df["yoy_pct"].median()
bcg_df["bcg_label"] = bcg_df.apply(
    lambda r: "Stars" if r.market_share_pct>=med_s and r.yoy_pct>=med_g
    else ("Cash Cows" if r.market_share_pct>=med_s
    else ("Question Marks" if r.yoy_pct>=med_g else "Dogs")), axis=1)
bcg_df = bcg_df.reset_index()
bcg_df["group_name"] = bcg_df["group_code"].map(
    fact[["group_code","group_name"]].drop_duplicates().set_index("group_code")["group_name"])
save(bcg_df, "41_bcg_matrix.csv")

# 42 — so sánh Q1/2025 vs Q1/2026 chi tiết (tỉnh × nhóm)
q1_cmp = []
for yr in [2025, 2026]:
    sub = fact[(fact.fiscal_year==yr) & (fact.fiscal_quarter==1)]
    grp = (sub.groupby(["province_name","region","group_code"])
           .agg(tong_dt=("line_total","sum"), tong_sl=("quantity","sum"),
                so_don=("so_number","nunique"))
           .reset_index())
    grp["year"] = yr
    q1_cmp.append(grp)
q1_wide = pd.concat(q1_cmp)
save(q1_wide, "42_q1_comparison_province_group.csv")

# 43 — so sánh MoM chi tiết × nhóm
monthly_mom = monthly_grp.copy()
monthly_mom["tong_dt_prev"] = (monthly_mom.groupby("group_code")["tong_dt"].shift(1))
monthly_mom["mom_pct"] = ((monthly_mom["tong_dt"] - monthly_mom["tong_dt_prev"])
                           / monthly_mom["tong_dt_prev"].replace(0, np.nan) * 100).round(1)
save(monthly_mom, "43_mom_growth_by_group.csv")

# ─────────────────────────────────────────────────────────────────────────────
# NHÓM 7 — DỰ BÁO
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Nhóm 7: Dự báo ──")

# 44 — dự báo màu Q2
from analytics.forecasting.color_forecast import forecast_color_q2, slow_moving_sku, top_colors_per_group
color_q2 = forecast_color_q2(fact)
color_q2["group_name"] = color_q2["group_code"].map(
    fact[["group_code","group_name"]].drop_duplicates().set_index("group_code")["group_name"])
color_q2["rank_trong_nhom"] = color_q2.groupby("group_code")["du_bao_q2_pct"].rank(ascending=False).astype(int)
save(color_q2.sort_values(["group_code","du_bao_q2_pct"], ascending=[True,False]),
     "44_color_forecast_q2.csv")

# 45 — SKU bán chậm
slow = slow_moving_sku(fact, threshold_qty=20)
slow["group_name"] = slow["group_code"].map(
    fact[["group_code","group_name"]].drop_duplicates().set_index("group_code")["group_name"])
save(slow.sort_values("quantity"), "45_slow_moving_sku.csv")

# 46 — top màu theo nhóm
top_colors = top_colors_per_group(fact, top_n=5)
top_colors["group_name"] = top_colors["group_code"].map(
    fact[["group_code","group_name"]].drop_duplicates().set_index("group_code")["group_name"])
save(top_colors, "46_top_colors_per_group.csv")

# 47 — Prophet Q2/2026 daily
from analytics.forecasting.demand_forecast import prepare_series, forecast_group
prophet_rows = []
print("  Đang chạy Prophet cho 5 nhóm SP...")
for grp in ["CITYBIKE_P","KIDBIKE_1","KIDBIKE_2","SPORTBIKE_S","SPORTBIKE_A"]:
    ts = prepare_series(fact, grp)
    try:
        fc = forecast_group(ts, periods=91)
        fc["group_code"] = grp
        fc["is_forecast"] = (fc["ds"] >= "2026-03-01").astype(int)
        prophet_rows.append(fc)
        print(f"    ✓ {grp}")
    except Exception as e:
        print(f"    ✗ {grp}: {e}")
if prophet_rows:
    prophet_all = pd.concat(prophet_rows, ignore_index=True)
    prophet_all["group_name"] = prophet_all["group_code"].map(
        fact[["group_code","group_name"]].drop_duplicates().set_index("group_code")["group_name"])
    save(prophet_all.sort_values(["group_code","ds"]), "47_prophet_forecast_daily.csv")

    # 48 — Prophet Q2 tổng hợp theo tháng
    q2_fc = prophet_all[(prophet_all["ds"] >= "2026-04-01") & (prophet_all["ds"] <= "2026-06-30")].copy()
    q2_fc["month"] = q2_fc["ds"].dt.month
    q2_monthly = (q2_fc.groupby(["group_code","group_name","month"])
                  .agg(du_bao_dt=("yhat","sum"),
                       lower_80=("yhat_lower","sum"),
                       upper_80=("yhat_upper","sum"))
                  .reset_index())
    q2_monthly["month_label"] = "T" + q2_monthly["month"].astype(str) + "/2026"
    save(q2_monthly, "48_prophet_q2_monthly_summary.csv")

    # 49 — Prophet Q2 tổng hợp theo nhóm
    q2_grp = (q2_fc.groupby(["group_code","group_name"])
              .agg(du_bao_q2=("yhat","sum"),
                   lower_80=("yhat_lower","sum"),
                   upper_80=("yhat_upper","sum"))
              .reset_index())
    q2_grp["q1_2026_actual"] = q2_grp["group_code"].map(
        fact[(fact.fiscal_year==2026)&(fact.fiscal_quarter==1)]
        .groupby("group_code")["line_total"].sum())
    q2_grp["qoq_est_pct"] = ((q2_grp["du_bao_q2"] - q2_grp["q1_2026_actual"])
                               / q2_grp["q1_2026_actual"].replace(0,1) * 100).round(1)
    save(q2_grp, "49_prophet_q2_group_summary.csv")

# 50 — Churn prediction
from analytics.forecasting.dealer_forecast import build_dealer_features, label_churn, train_churn_model
feats = build_dealer_features(fact)
feats = label_churn(feats)
try:
    model, scaler, fp = train_churn_model(feats)
    cus_info = (fact[["customer_code","customer_name","province_name","region","group_code"]]
                .groupby("customer_code").agg(
                    customer_name=("customer_name","first"),
                    province_name=("province_name","first"),
                    region=("region","first"),
                    so_nhom_sp=("group_code","nunique")).reset_index())
    fp = fp.merge(cus_info, on="customer_code", how="left")
    fp["churn_prob_pct"] = (fp["churn_prob"]*100).round(1)
    fp["risk_level"] = fp["churn_prob"].apply(
        lambda p: "Cao" if p>=0.6 else ("Trung binh" if p>=0.35 else "Thap"))
    fp["model_used"] = type(model).__name__
    save(fp.sort_values("churn_prob", ascending=False), "50_churn_prediction.csv")
    print(f"  Model: {type(model).__name__}")
except Exception as e:
    print(f"  Churn model error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# NHÓM 8 — CROSS-TAB / PIVOT NÂNG CAO
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Nhóm 8: Cross-tab nâng cao ──")

# 51 — đại lý × SKU (top 100 đại lý × top 30 SKU)
top100_cus = rfm.nlargest(100,"tong_dt")["customer_code"].tolist()
top30_sku  = prod_stats.nlargest(30,"tong_dt")["product_code"].tolist()
cus_sku    = (fact[fact["customer_code"].isin(top100_cus) & fact["product_code"].isin(top30_sku)]
              .groupby(["customer_code","customer_name","product_code","product_name","color"])
              .agg(tong_sl=("quantity","sum"), tong_dt=("line_total","sum"))
              .reset_index())
save(cus_sku, "51_top100dealer_x_top30sku.csv")

# 52 — tỉnh × SKU (top 20 tỉnh × top 30 SKU)
top20_prov = prov_stats.nlargest(20,"tong_dt")["province_name"].tolist()
prov_sku   = (fact[fact["province_name"].isin(top20_prov) & fact["product_code"].isin(top30_sku)]
              .groupby(["province_name","region","product_code","product_name"])
              .agg(tong_sl=("quantity","sum"), tong_dt=("line_total","sum"))
              .reset_index())
save(prov_sku, "52_top20province_x_top30sku.csv")

# 53 — co-purchase matrix nhóm SP × nhóm SP
cp = (fact.groupby("so_number")["group_code"]
      .apply(lambda x: list(set(x))).reset_index())
cp_rows = []
for _, row in cp.iterrows():
    grps = row["group_code"]
    for i in range(len(grps)):
        for j in range(len(grps)):
            cp_rows.append({"group_a": grps[i], "group_b": grps[j]})
cp_matrix = (pd.DataFrame(cp_rows)
             .groupby(["group_a","group_b"]).size()
             .reset_index(name="so_don_cung_xuat_hien"))
save(cp_matrix, "53_copurchase_matrix.csv")

# 54 — pivot co-purchase (wide)
pivot_cp = cp_matrix.pivot(index="group_a", columns="group_b",
                            values="so_don_cung_xuat_hien").fillna(0)
pivot_cp.index.name = "Nhom_SP"
save(pivot_cp.reset_index(), "54_pivot_copurchase.csv")

# 55 — KPI tổng hợp cuối cùng
kpi = {
    "tong_doanh_thu_vnd":        fact["line_total"].sum(),
    "tong_doanh_thu_ty":         round(fact["line_total"].sum()/1e9, 2),
    "tong_san_luong_chiec":      int(fact["quantity"].sum()),
    "tong_don_hang":             fact["so_number"].nunique(),
    "tong_dai_ly":               fact["customer_code"].nunique(),
    "tong_sku_ban_duoc":         fact["product_code"].nunique(),
    "tong_tinh_co_doanh_so":     fact["province_name"].dropna().nunique(),
    "gia_ban_trung_binh":        round(fact["line_total"].sum()/fact["quantity"].sum(),0),
    "dt_tb_moi_dai_ly":          round(fact["line_total"].sum()/fact["customer_code"].nunique(),0),
    "dt_tb_moi_don":             round(fact["line_total"].sum()/fact["so_number"].nunique(),0),
    "sl_tb_moi_don":             round(fact["quantity"].sum()/fact["so_number"].nunique(),1),
    "ngay_bat_dau":              str(fact["order_date"].min().date()),
    "ngay_ket_thuc":             str(fact["order_date"].max().date()),
    "so_thang_du_lieu":          fact["ym"].nunique(),
    "nhom_sp_cao_nhat":          fact.groupby("group_code")["line_total"].sum().idxmax(),
    "tinh_cao_nhat":             fact.groupby("province_name")["line_total"].sum().idxmax(),
    "dai_ly_cao_nhat":           rfm.nlargest(1,"tong_dt")["customer_name"].iloc[0],
    "sku_ban_chay_nhat":         prod_stats.nlargest(1,"tong_sl")["product_name"].iloc[0],
    "mau_ban_chay_nhat":         fact.groupby("color")["quantity"].sum().idxmax() if "color" in fact.columns else "N/A",
}
save(pd.DataFrame([kpi]).T.reset_index().rename(columns={"index":"chi_so",0:"gia_tri"}),
     "55_kpi_tong_hop.csv")

# ─────────────────────────────────────────────────────────────────────────────
print(f"""
{'='*65}
✅  HOÀN THÀNH — {len(list(OUT.glob('*.csv')))} file CSV
{'='*65}
📁  {OUT}
""")
for f in sorted(OUT.glob("*.csv")):
    rows = sum(1 for _ in open(f, encoding="utf-8-sig")) - 1
    print(f"  {f.name:<55} {rows:>7,} dòng")
print(f"\n{'='*65}")
