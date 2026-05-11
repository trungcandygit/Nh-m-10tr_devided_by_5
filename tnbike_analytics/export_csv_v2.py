"""
Xuất 5 file CSV siêu lớn — mỗi file gộp nhiều chiều phân tích
Chạy: python export_csv_v2.py
"""
import warnings, logging, sys, os
warnings.filterwarnings("ignore"); logging.disable(logging.CRITICAL)
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
from pathlib import Path
from analytics.sql_data_loader import load_all, build_fact

OUT = Path("output/csv5")
OUT.mkdir(parents=True, exist_ok=True)

def save(df, name):
    p = OUT / name
    df.to_csv(p, index=False, encoding="utf-8-sig")
    size_kb = p.stat().st_size // 1024
    print(f"  ✓ {name:<45} {len(df):>8,} dòng   {size_kb:>6,} KB")

print("⏳ Tải dữ liệu...")
dfs  = load_all()
fact = build_fact(dfs)
fact["order_date"] = pd.to_datetime(fact["order_date"])
fact["ym"]     = fact["fiscal_year"].astype(str) + "-" + fact["fiscal_month"].astype(str).str.zfill(2)
fact["week"]   = fact["order_date"].dt.isocalendar().week.astype(int)
fact["dow"]    = fact["order_date"].dt.day_name()
fact["dom"]    = fact["order_date"].dt.day
fact["q_label"]= "Q" + fact["fiscal_quarter"].astype(str) + "/" + fact["fiscal_year"].astype(str)
print(f"  → {len(fact):,} dòng gốc\n")

# ─────────────────────────────────────────────────────────────────────────────
# FILE 1 — FACT SALES SIÊU ĐẦY ĐỦ (1 dòng = 1 dòng hàng)
# Thêm toàn bộ computed fields: RFM segment, ABC rank, % ty trọng, rank tỉnh...
# ─────────────────────────────────────────────────────────────────────────────
print("── File 1: fact_sales_master ──")

# RFM segment cho mỗi đại lý
ref_date = fact["order_date"].max() + pd.Timedelta(days=1)
rfm_base = fact.groupby("customer_code").agg(
    recency=("order_date", lambda x: (ref_date - x.max()).days),
    freq=("so_number", "nunique"),
    monetary=("line_total", "sum")
).reset_index()
rfm_base["R"] = pd.qcut(rfm_base["recency"], 5, labels=[5,4,3,2,1]).astype(int)
rfm_base["F"] = pd.qcut(rfm_base["freq"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
rfm_base["M"] = pd.qcut(rfm_base["monetary"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
SEG = {(5,5):"Champions",(5,4):"Champions",(4,5):"Loyal",(4,4):"Loyal",
       (4,3):"Loyal",(3,5):"Co tiem nang",(3,4):"Co tiem nang",
       (5,3):"Moi gan day",(2,5):"Nguy co roi bo",(2,4):"Nguy co roi bo",
       (2,3):"Nguy co roi bo",(1,5):"Khong the mat",(1,4):"Khong the mat",
       (2,2):"Ngu dong",(1,3):"Ngu dong",(1,2):"Da mat",(1,1):"Da mat"}
rfm_base["segment"] = rfm_base.apply(lambda r: SEG.get((r.R, r.F), "Trung binh"), axis=1)
rfm_base["rfm_score"] = rfm_base["R"].astype(str)+rfm_base["F"].astype(str)+rfm_base["M"].astype(str)
rfm_base["rfm_sum"] = rfm_base["R"]+rfm_base["F"]+rfm_base["M"]

# ABC rank cho SKU
sku_rev = fact.groupby("product_code")["line_total"].sum().sort_values(ascending=False)
sku_cumul = (sku_rev.cumsum() / sku_rev.sum() * 100)
sku_abc = pd.cut(sku_cumul, bins=[0,70,90,100], labels=["A","B","C"]).rename("abc_rank")
sku_rank = sku_rev.rank(ascending=False).astype(int).rename("sku_rank_dt")

# Province rank
prov_rev  = fact.groupby("province_name")["line_total"].sum()
prov_rank = prov_rev.rank(ascending=False).astype(int).rename("province_rank")

# Month-over-Month doanh thu nhóm SP
monthly_grp = (fact.groupby(["ym","group_code"])["line_total"].sum()
               .reset_index().sort_values(["group_code","ym"]))
monthly_grp["mom_pct_nhom"] = (monthly_grp.groupby("group_code")["line_total"]
                                .pct_change().mul(100).round(1))
mom_lookup = monthly_grp.set_index(["ym","group_code"])["mom_pct_nhom"]

# Dán vào fact
f1 = fact.merge(
    rfm_base[["customer_code","R","F","M","rfm_score","rfm_sum","segment","recency","freq","monetary"]],
    on="customer_code", how="left"
)
f1["sku_abc_rank"]    = f1["product_code"].map(sku_abc)
f1["sku_rank_dt"]     = f1["product_code"].map(sku_rank)
f1["province_rank"]   = f1["province_name"].map(prov_rank)
f1["mom_pct_nhom"]    = [mom_lookup.get((r.ym, r.group_code), np.nan) for _, r in f1.iterrows()]

# Tỷ trọng line_total trong tháng
month_total = f1.groupby("ym")["line_total"].transform("sum")
grp_month_total = f1.groupby(["ym","group_code"])["line_total"].transform("sum")
f1["ty_trong_thang_pct"]     = (f1["line_total"] / month_total * 100).round(4)
f1["ty_trong_nhom_thang_pct"]= (f1["line_total"] / grp_month_total * 100).round(4)
f1["don_gia_segment"]        = pd.cut(f1["unit_price"],
    bins=[0,1e6,2e6,3e6,5e6,1e9],
    labels=["<1tr","1-2tr","2-3tr","3-5tr",">5tr"])
f1["is_high_value_order"] = (f1["line_total"] >= f1["line_total"].quantile(0.75)).astype(int)
f1["is_top_sku"]          = (f1["sku_abc_rank"] == "A").astype(int)

cols_order = [
    "so_number","order_date","ym","fiscal_year","fiscal_month","fiscal_quarter","q_label",
    "week","dow","dom",
    "customer_code","customer_name","province_name","province_rank","region",
    "segment","R","F","M","rfm_score","rfm_sum","recency","freq","monetary",
    "product_code","product_name","color","line_id","line_name","group_code","group_name",
    "sku_abc_rank","sku_rank_dt",
    "quantity","unit_price","line_total","don_gia_segment",
    "ty_trong_thang_pct","ty_trong_nhom_thang_pct","mom_pct_nhom",
    "is_high_value_order","is_top_sku"
]
save(f1[cols_order].sort_values(["order_date","so_number"]),
     "01_fact_sales_master.csv")


# ─────────────────────────────────────────────────────────────────────────────
# FILE 2 — TIME SERIES STACK (mọi chiều thời gian gộp chung)
# grain: daily | weekly | monthly | quarterly + dimension: total|group|province|region|line|color
# ─────────────────────────────────────────────────────────────────────────────
print("\n── File 2: time_series_all ──")

chunks = []

def _chunk(df, grain, dimension):
    df = df.copy()
    df["grain"]     = grain
    df["dimension"] = dimension
    return df

# ── Daily × group
dg = (fact.groupby(["order_date","ym","fiscal_year","fiscal_month","fiscal_quarter",
                     "week","dow","dom","group_code","group_name"])
      .agg(so_don=("so_number","nunique"), tong_sl=("quantity","sum"),
           tong_dt=("line_total","sum"), so_dai_ly=("customer_code","nunique"),
           so_sku=("product_code","nunique")).reset_index())
chunks.append(_chunk(dg, "daily", "group"))

# ── Daily × region
dr = (fact.groupby(["order_date","ym","fiscal_year","fiscal_month","fiscal_quarter","week","dow","dom","region"])
      .agg(so_don=("so_number","nunique"), tong_sl=("quantity","sum"),
           tong_dt=("line_total","sum"), so_dai_ly=("customer_code","nunique")).reset_index())
chunks.append(_chunk(dr, "daily", "region"))

# ── Daily total
dt = (fact.groupby(["order_date","ym","fiscal_year","fiscal_month","fiscal_quarter","week","dow","dom"])
      .agg(so_don=("so_number","nunique"), tong_sl=("quantity","sum"),
           tong_dt=("line_total","sum"), so_dai_ly=("customer_code","nunique"),
           so_sku=("product_code","nunique")).reset_index())
chunks.append(_chunk(dt, "daily", "total"))

# ── Weekly × group
wg = (fact.groupby(["fiscal_year","week","group_code","group_name"])
      .agg(so_don=("so_number","nunique"), tong_sl=("quantity","sum"),
           tong_dt=("line_total","sum"), so_dai_ly=("customer_code","nunique")).reset_index())
chunks.append(_chunk(wg, "weekly", "group"))

# ── Monthly × group
mg = (fact.groupby(["fiscal_year","fiscal_month","ym","group_code","group_name"])
      .agg(so_don=("so_number","nunique"), tong_sl=("quantity","sum"),
           tong_dt=("line_total","sum"), so_dai_ly=("customer_code","nunique"),
           so_sku=("product_code","nunique")).reset_index())
mg_prev = mg.copy(); mg_prev["tong_dt_prev"] = mg.groupby("group_code")["tong_dt"].shift(1)
mg_prev["mom_pct"] = ((mg_prev["tong_dt"]-mg_prev["tong_dt_prev"])/mg_prev["tong_dt_prev"].replace(0,np.nan)*100).round(1)
chunks.append(_chunk(mg_prev, "monthly", "group"))

# ── Monthly × province
mp = (fact.groupby(["fiscal_year","fiscal_month","ym","province_name","region"])
      .agg(so_don=("so_number","nunique"), tong_sl=("quantity","sum"),
           tong_dt=("line_total","sum"), so_dai_ly=("customer_code","nunique")).reset_index())
chunks.append(_chunk(mp, "monthly", "province"))

# ── Monthly × line
ml = (fact.groupby(["fiscal_year","fiscal_month","ym","line_name","group_code"])
      .agg(so_don=("so_number","nunique"), tong_sl=("quantity","sum"),
           tong_dt=("line_total","sum")).reset_index())
chunks.append(_chunk(ml, "monthly", "line"))

# ── Monthly × color × group
mc = (fact[fact["color"].notna() & (fact["color"]!="")]
      .groupby(["fiscal_year","fiscal_month","ym","group_code","color"])
      .agg(tong_sl=("quantity","sum"), tong_dt=("line_total","sum")).reset_index())
chunks.append(_chunk(mc, "monthly", "color_group"))

# ── Monthly × region × group
mrg = (fact.groupby(["fiscal_year","fiscal_month","ym","region","group_code"])
       .agg(tong_sl=("quantity","sum"), tong_dt=("line_total","sum"),
            so_don=("so_number","nunique")).reset_index())
chunks.append(_chunk(mrg, "monthly", "region_group"))

# ── Quarterly × group
qg = (fact.groupby(["fiscal_year","fiscal_quarter","q_label","group_code","group_name"])
      .agg(so_don=("so_number","nunique"), tong_sl=("quantity","sum"),
           tong_dt=("line_total","sum"), so_dai_ly=("customer_code","nunique")).reset_index())
chunks.append(_chunk(qg, "quarterly", "group"))

# ── Quarterly × province
qp = (fact.groupby(["fiscal_year","fiscal_quarter","q_label","province_name","region"])
      .agg(so_don=("so_number","nunique"), tong_sl=("quantity","sum"),
           tong_dt=("line_total","sum"), so_dai_ly=("customer_code","nunique")).reset_index())
chunks.append(_chunk(qp, "quarterly", "province"))

# ── Quarterly × region
qr = (fact.groupby(["fiscal_year","fiscal_quarter","q_label","region"])
      .agg(so_don=("so_number","nunique"), tong_sl=("quantity","sum"),
           tong_dt=("line_total","sum"), so_dai_ly=("customer_code","nunique"),
           so_tinh=("province_name","nunique")).reset_index())
chunks.append(_chunk(qr, "quarterly", "region"))

# ── Monthly total
mt = (fact.groupby(["fiscal_year","fiscal_month","ym"])
      .agg(so_don=("so_number","nunique"), tong_sl=("quantity","sum"),
           tong_dt=("line_total","sum"), so_dai_ly=("customer_code","nunique"),
           so_sku=("product_code","nunique"), so_tinh=("province_name","nunique")).reset_index())
mt["mom_pct"] = mt["tong_dt"].pct_change().mul(100).round(1)
chunks.append(_chunk(mt, "monthly", "total"))

# ── DOW
dow = (fact.groupby(["dow","fiscal_year"])
       .agg(so_don=("so_number","nunique"), tong_sl=("quantity","sum"),
            tong_dt=("line_total","sum")).reset_index())
chunks.append(_chunk(dow, "pattern", "day_of_week"))

# ── DOM
dom = (fact.groupby(["dom","fiscal_year"])
       .agg(so_don=("so_number","nunique"), tong_sl=("quantity","sum"),
            tong_dt=("line_total","sum")).reset_index())
chunks.append(_chunk(dom, "pattern", "day_of_month"))

ts_all = pd.concat(chunks, ignore_index=True)
save(ts_all.sort_values(["grain","dimension","fiscal_year","fiscal_month"],
                         na_position="last"),
     "02_time_series_all.csv")


# ─────────────────────────────────────────────────────────────────────────────
# FILE 3 — PRODUCT & GEO MATRIX (mọi cross-tab sản phẩm × địa lý)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── File 3: product_geo_matrix ──")

pg_chunks = []

# SKU × province × year (chi tiết nhất)
sku_prov = (fact.groupby(["product_code","product_name","color","line_name",
                           "group_code","group_name","province_name","region",
                           "fiscal_year","fiscal_month","ym"])
            .agg(tong_sl=("quantity","sum"), tong_dt=("line_total","sum"),
                 so_don=("so_number","nunique"), so_dai_ly=("customer_code","nunique"))
            .reset_index())
sku_prov["level"] = "sku_province_month"
pg_chunks.append(sku_prov)

# SKU × region × month
sku_reg = (fact.groupby(["product_code","product_name","color","group_code",
                          "region","fiscal_year","fiscal_month","ym"])
           .agg(tong_sl=("quantity","sum"), tong_dt=("line_total","sum"),
                so_don=("so_number","nunique")).reset_index())
sku_reg["level"] = "sku_region_month"
pg_chunks.append(sku_reg)

# Line × province × month
line_prov = (fact.groupby(["line_name","group_code","province_name","region",
                            "fiscal_year","fiscal_month","ym"])
             .agg(tong_sl=("quantity","sum"), tong_dt=("line_total","sum"),
                  so_don=("so_number","nunique")).reset_index())
line_prov["level"] = "line_province_month"
pg_chunks.append(line_prov)

# Group × province × month
grp_prov = (fact.groupby(["group_code","group_name","province_name","region",
                           "fiscal_year","fiscal_month","ym"])
            .agg(tong_sl=("quantity","sum"), tong_dt=("line_total","sum"),
                 so_don=("so_number","nunique"), so_dai_ly=("customer_code","nunique"))
            .reset_index())
grp_prov["level"] = "group_province_month"
pg_chunks.append(grp_prov)

# Color × province × month
color_prov = (fact[fact["color"].notna() & (fact["color"]!="")]
              .groupby(["color","group_code","province_name","region",
                        "fiscal_year","fiscal_month","ym"])
              .agg(tong_sl=("quantity","sum"), tong_dt=("line_total","sum")).reset_index())
color_prov["level"] = "color_province_month"
pg_chunks.append(color_prov)

# SKU × quarter
sku_qtr = (fact.groupby(["product_code","product_name","color","line_name",
                          "group_code","fiscal_year","fiscal_quarter","q_label"])
           .agg(tong_sl=("quantity","sum"), tong_dt=("line_total","sum"),
                so_don=("so_number","nunique"), so_tinh=("province_name","nunique"),
                so_dai_ly=("customer_code","nunique")).reset_index())
sku_qtr["level"] = "sku_quarter"
pg_chunks.append(sku_qtr)

# Price segment × province × month
fact["price_segment"] = pd.cut(fact["unit_price"],
    bins=[0,1e6,2e6,3e6,5e6,1e9],
    labels=["<1tr","1-2tr","2-3tr","3-5tr",">5tr"])
price_prov = (fact.groupby(["price_segment","group_code","province_name","region",
                             "fiscal_year","fiscal_month"])
              .agg(tong_sl=("quantity","sum"), tong_dt=("line_total","sum"),
                   so_don=("so_number","nunique")).reset_index())
price_prov["level"] = "price_segment_province_month"
pg_chunks.append(price_prov)

pg_all = pd.concat(pg_chunks, ignore_index=True)
save(pg_all.sort_values(["level","group_code","fiscal_year","fiscal_month"],
                         na_position="last"),
     "03_product_geo_matrix.csv")


# ─────────────────────────────────────────────────────────────────────────────
# FILE 4 — CUSTOMER DEEP DIVE (RFM + hành vi mua + basket)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── File 4: customer_deep_dive ──")

cus_chunks = []

# RFM full mỗi đại lý
rfm_full = fact.groupby(["customer_code","customer_name","province_name","region"]).agg(
    ngay_dau=("order_date","min"), ngay_cuoi=("order_date","max"),
    so_don=("so_number","nunique"),
    tong_sl=("quantity","sum"), tong_dt=("line_total","sum"),
    so_nhom_sp=("group_code","nunique"), so_sku=("product_code","nunique"),
    so_tinh_ban=("province_name","first"),
    gia_tb=("unit_price","mean"), gia_max=("unit_price","max"),
    don_tb_tien=("line_total","mean"), don_tb_sl=("quantity","mean"),
).reset_index()
rfm_full["recency"]   = (ref_date - rfm_full["ngay_cuoi"]).dt.days
rfm_full["lifespan"]  = (rfm_full["ngay_cuoi"] - rfm_full["ngay_dau"]).dt.days
rfm_full["R"] = pd.qcut(rfm_full["recency"], 5, labels=[5,4,3,2,1]).astype(int)
rfm_full["F"] = pd.qcut(rfm_full["so_don"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
rfm_full["M"] = pd.qcut(rfm_full["tong_dt"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
rfm_full["rfm_score"] = rfm_full["R"].astype(str)+rfm_full["F"].astype(str)+rfm_full["M"].astype(str)
rfm_full["rfm_sum"]   = rfm_full["R"]+rfm_full["F"]+rfm_full["M"]
rfm_full["segment"]   = rfm_full.apply(lambda r: SEG.get((r.R, r.F), "Trung binh"), axis=1)
rfm_full["clv_est"]   = (rfm_full["tong_dt"] / rfm_full["lifespan"].replace(0,1) * 365).round(0)
rfm_full["dt_tb_don"] = (rfm_full["tong_dt"] / rfm_full["so_don"]).round(0)
rfm_full["rank_dt"]   = rfm_full["tong_dt"].rank(ascending=False).astype(int)
rfm_full["cumul_pct"] = (rfm_full.sort_values("tong_dt",ascending=False)["tong_dt"]
                         .cumsum() / rfm_full["tong_dt"].sum() * 100).values
rfm_full["pareto_group"] = pd.cut(rfm_full["cumul_pct"].fillna(100),
    bins=[0,50,80,95,100], labels=["Top50%","50-80%","80-95%","Bot5%"])
rfm_full["cohort_month"] = rfm_full["ngay_dau"].dt.to_period("M").astype(str)
rfm_full["level"] = "rfm_customer"
cus_chunks.append(rfm_full)

# Customer × month × group (hành vi mua theo tháng từng nhóm SP)
cus_mg = (fact.groupby(["customer_code","customer_name","province_name","region",
                          "fiscal_year","fiscal_month","ym","group_code","group_name"])
          .agg(so_don=("so_number","nunique"), tong_sl=("quantity","sum"),
               tong_dt=("line_total","sum"), so_sku=("product_code","nunique"))
          .reset_index())
cus_mg["level"] = "customer_month_group"
cus_chunks.append(cus_mg)

# Customer × SKU (mỗi SKU từng đại lý đã mua bao giờ)
cus_sku = (fact.groupby(["customer_code","customer_name","province_name","region",
                          "product_code","product_name","color","group_code"])
           .agg(tong_sl=("quantity","sum"), tong_dt=("line_total","sum"),
                so_don=("so_number","nunique"),
                lan_dau=("order_date","min"), lan_cuoi=("order_date","max"))
           .reset_index())
cus_sku["level"] = "customer_sku"
cus_chunks.append(cus_sku)

# Basket analysis (mỗi đơn hàng)
basket = (fact.groupby(["so_number","order_date","ym","fiscal_year","fiscal_month",
                         "customer_code","customer_name","province_name","region"])
          .agg(so_dong=("product_code","count"), so_sku=("product_code","nunique"),
               so_nhom_sp=("group_code","nunique"),
               tong_sl=("quantity","sum"), tong_tien=("line_total","sum"),
               gia_min=("unit_price","min"), gia_max=("unit_price","max"))
          .reset_index())
basket["aov"]            = (basket["tong_tien"] / basket["so_dong"]).round(0)
basket["is_cross_sell"]  = (basket["so_nhom_sp"] > 1).astype(int)
basket["basket_size_cat"]= pd.cut(basket["so_dong"], bins=[0,3,7,15,999],
                                   labels=["Small","Medium","Large","XLarge"])
basket["level"] = "basket_order"
cus_chunks.append(basket)

# Customer × quarter (quarterly spending)
cus_qtr = (fact.groupby(["customer_code","customer_name","province_name","region",
                           "fiscal_year","fiscal_quarter","q_label"])
           .agg(so_don=("so_number","nunique"), tong_sl=("quantity","sum"),
                tong_dt=("line_total","sum"), so_sku=("product_code","nunique"),
                so_nhom_sp=("group_code","nunique")).reset_index())
cus_qtr["level"] = "customer_quarter"
cus_chunks.append(cus_qtr)

# Cohort retention (tháng đầu tiên → các tháng sau)
cohort_base = rfm_full[["customer_code","cohort_month"]].copy()
cus_monthly_all = (fact.groupby(["customer_code","ym"])["line_total"]
                   .sum().reset_index())
cohort_ret = cus_monthly_all.merge(cohort_base, on="customer_code")
cohort_ret["months_since_start"] = cohort_ret.apply(
    lambda r: (pd.Period(r.ym,"M") - pd.Period(r.cohort_month,"M")).n, axis=1)
cohort_agg = (cohort_ret.groupby(["cohort_month","months_since_start"])
              .agg(so_dai_ly=("customer_code","nunique"),
                   tong_dt=("line_total","sum")).reset_index())
cohort_size = cohort_agg[cohort_agg["months_since_start"]==0][["cohort_month","so_dai_ly"]].rename(columns={"so_dai_ly":"cohort_size"})
cohort_agg  = cohort_agg.merge(cohort_size, on="cohort_month")
cohort_agg["retention_rate"] = (cohort_agg["so_dai_ly"] / cohort_agg["cohort_size"] * 100).round(1)
cohort_agg["level"] = "cohort_retention"
cus_chunks.append(cohort_agg)

cus_all = pd.concat(cus_chunks, ignore_index=True)
save(cus_all.sort_values(["level","customer_code","fiscal_year","fiscal_month"],
                          na_position="last"),
     "04_customer_deep_dive.csv")


# ─────────────────────────────────────────────────────────────────────────────
# FILE 5 — FORECAST + ANALYTICS NÂNG CAO
# BCG, YoY, Co-purchase, Prophet, Color forecast, Churn, Price tier, ABC
# ─────────────────────────────────────────────────────────────────────────────
print("\n── File 5: forecast_analytics ──")

fa_chunks = []

# ── BCG chi tiết
rev_2025  = fact[fact.fiscal_year==2025].groupby("group_code")["line_total"].sum()
rev_q1_25 = fact[(fact.fiscal_year==2025)&(fact.fiscal_quarter==1)].groupby("group_code")["line_total"].sum()
rev_q1_26 = fact[(fact.fiscal_year==2026)&(fact.fiscal_quarter==1)].groupby("group_code")["line_total"].sum()
sl_2025   = fact[fact.fiscal_year==2025].groupby("group_code")["quantity"].sum()
bcg = pd.DataFrame({"rev_2025":rev_2025,"rev_q1_2025":rev_q1_25,
                    "rev_q1_2026":rev_q1_26,"sl_2025":sl_2025}).fillna(0)
bcg["market_share_pct"] = (bcg["rev_2025"]/bcg["rev_2025"].sum()*100).round(2)
bcg["sl_share_pct"]     = (bcg["sl_2025"]/bcg["sl_2025"].sum()*100).round(2)
bcg["yoy_pct"]          = ((bcg["rev_q1_2026"]-bcg["rev_q1_2025"])/bcg["rev_q1_2025"].replace(0,1)*100).round(1)
med_s = bcg["market_share_pct"].median(); med_g = bcg["yoy_pct"].median()
bcg["bcg_label"] = bcg.apply(lambda r:
    "Stars" if r.market_share_pct>=med_s and r.yoy_pct>=med_g else
    ("Cash Cows" if r.market_share_pct>=med_s else
    ("Question Marks" if r.yoy_pct>=med_g else "Dogs")), axis=1)
bcg = bcg.reset_index()
bcg["group_name"] = bcg["group_code"].map(fact[["group_code","group_name"]].drop_duplicates().set_index("group_code")["group_name"])
bcg["analytic_type"] = "bcg_matrix"
fa_chunks.append(bcg)

# ── YoY tỉnh × nhóm (mọi combo)
q1_all = []
for yr in [2025,2026]:
    sub = fact[(fact.fiscal_year==yr)&(fact.fiscal_quarter==1)]
    g = sub.groupby(["province_name","region","group_code","group_name"]).agg(
        tong_dt=("line_total","sum"), tong_sl=("quantity","sum"),
        so_don=("so_number","nunique"), so_dai_ly=("customer_code","nunique")).reset_index()
    g["fiscal_year"] = yr; q1_all.append(g)
yoy = pd.concat(q1_all)
yoy_wide = yoy.pivot_table(index=["province_name","region","group_code","group_name"],
                            columns="fiscal_year", values="tong_dt", fill_value=0).reset_index()
yoy_wide.columns = ["province_name","region","group_code","group_name","tong_dt_2025","tong_dt_2026"]
yoy_wide["yoy_pct"] = ((yoy_wide["tong_dt_2026"]-yoy_wide["tong_dt_2025"])
                        / yoy_wide["tong_dt_2025"].replace(0,1)*100).round(1)
yoy_wide["yoy_abs"]  = (yoy_wide["tong_dt_2026"]-yoy_wide["tong_dt_2025"]).round(0)
yoy_wide["analytic_type"] = "yoy_q1_province_group"
fa_chunks.append(yoy_wide)

# ── Co-purchase matrix (group × group)
cp_rows = []
for so, grp in fact.groupby("so_number")["group_code"].apply(lambda x: list(set(x))).items():
    for a in grp:
        for b in grp:
            cp_rows.append({"group_a":a,"group_b":b,"so_number":so})
cp_df = (pd.DataFrame(cp_rows).groupby(["group_a","group_b"])
         .agg(so_don=("so_number","nunique")).reset_index())
cp_df["support_pct"] = (cp_df["so_don"] / fact["so_number"].nunique() * 100).round(2)
cp_df["analytic_type"] = "copurchase_matrix"
fa_chunks.append(cp_df)

# ── Color forecast Q2 + historical
from analytics.forecasting.color_forecast import forecast_color_q2, slow_moving_sku
color_q2 = forecast_color_q2(fact)
color_q2["group_name"] = color_q2["group_code"].map(
    fact[["group_code","group_name"]].drop_duplicates().set_index("group_code")["group_name"])
color_q2["rank_nhom"] = color_q2.groupby("group_code")["du_bao_q2_pct"].rank(ascending=False).astype(int)
color_q2["analytic_type"] = "color_forecast_q2"
fa_chunks.append(color_q2)

# Color historical (T1-T3/2026 actual)
color_hist = (fact[fact["color"].notna() & (fact["color"]!="")]
              .groupby(["group_code","group_name","color","fiscal_year","fiscal_month"])
              .agg(tong_sl=("quantity","sum"), tong_dt=("line_total","sum")).reset_index())
color_hist["ty_trong_nhom"] = (color_hist.groupby(["group_code","fiscal_year","fiscal_month"])["tong_sl"]
                                .transform(lambda x: x/x.sum()*100)).round(2)
color_hist["analytic_type"] = "color_historical"
fa_chunks.append(color_hist)

# ── Slow moving SKU
slow = slow_moving_sku(fact, threshold_qty=20)
slow["group_name"] = slow["group_code"].map(
    fact[["group_code","group_name"]].drop_duplicates().set_index("group_code")["group_name"])
slow["risk"] = slow["quantity"].apply(lambda q: "Xuat kho gap" if q==0 else ("Rat cham" if q<=5 else "Cham"))
slow["analytic_type"] = "slow_moving_sku"
fa_chunks.append(slow)

# ── Prophet forecast daily
from analytics.forecasting.demand_forecast import prepare_series, forecast_group
print("  Chạy Prophet...")
all_fc = []
for grp in ["CITYBIKE_P","KIDBIKE_1","KIDBIKE_2","SPORTBIKE_S","SPORTBIKE_A"]:
    ts = prepare_series(fact, grp)
    try:
        fc = forecast_group(ts, periods=91)
        fc["group_code"] = grp
        fc["is_forecast"] = (fc["ds"] >= "2026-03-01").astype(int)
        fc["group_name"] = fact[fact.group_code==grp]["group_name"].iloc[0]
        all_fc.append(fc)
        print(f"    ✓ {grp}")
    except Exception as e:
        print(f"    ✗ {grp}: {e}")

if all_fc:
    prophet = pd.concat(all_fc, ignore_index=True)
    prophet["month"]     = prophet["ds"].dt.month
    prophet["year"]      = prophet["ds"].dt.year
    prophet["ym"]        = prophet["year"].astype(str)+"-"+prophet["month"].astype(str).str.zfill(2)
    prophet["q"]         = prophet["ds"].dt.quarter
    prophet["analytic_type"] = "prophet_forecast"
    fa_chunks.append(prophet)

# ── Churn prediction
from analytics.forecasting.dealer_forecast import build_dealer_features, label_churn, train_churn_model
feats = build_dealer_features(fact)
feats = label_churn(feats)
try:
    model, scaler, fp = train_churn_model(feats)
    cus_info = (fact[["customer_code","customer_name","province_name","region"]]
                .drop_duplicates().groupby("customer_code").first().reset_index())
    fp = fp.merge(cus_info, on="customer_code", how="left")
    fp["churn_prob_pct"] = (fp["churn_prob"]*100).round(1)
    fp["risk_level"]  = fp["churn_prob"].apply(lambda p: "Cao" if p>=0.6 else ("TB" if p>=0.35 else "Thap"))
    fp["model_used"]  = type(model).__name__
    fp["rfm_segment"] = fp["customer_code"].map(rfm_base.set_index("customer_code")["segment"])
    fp["analytic_type"] = "churn_prediction"
    fa_chunks.append(fp)
    print(f"  Churn model: {type(model).__name__}")
except Exception as e:
    print(f"  Churn error: {e}")

# ── SKU ABC ranking + margin estimate
sku_abc_full = (fact.groupby(["product_code","product_name","color","line_name","group_code","group_name"])
                .agg(tong_sl=("quantity","sum"), tong_dt=("line_total","sum"),
                     so_don=("so_number","nunique"), so_dai_ly=("customer_code","nunique"),
                     so_tinh=("province_name","nunique"),
                     gia_tb=("unit_price","mean"), gia_min=("unit_price","min"),
                     gia_max=("unit_price","max")).reset_index())
sku_abc_full = sku_abc_full.sort_values("tong_dt", ascending=False)
sku_abc_full["rank"] = range(1, len(sku_abc_full)+1)
sku_abc_full["cumul_pct"] = (sku_abc_full["tong_dt"].cumsum()/sku_abc_full["tong_dt"].sum()*100).round(2)
sku_abc_full["abc"] = pd.cut(sku_abc_full["cumul_pct"], bins=[0,70,90,100], labels=["A","B","C"])
sku_abc_full["velocity"] = pd.cut(sku_abc_full["tong_sl"],
    bins=[0,50,200,500,99999], labels=["Lo","TB","Cao","Rat cao"])
sku_abc_full["analytic_type"] = "sku_abc_ranking"
fa_chunks.append(sku_abc_full)

# ── Price tier analysis × time
price_tier = (fact.groupby(["price_segment","group_code","group_name",
                             "fiscal_year","fiscal_month","ym","region"])
              .agg(tong_sl=("quantity","sum"), tong_dt=("line_total","sum"),
                   so_don=("so_number","nunique"), so_dai_ly=("customer_code","nunique"))
              .reset_index())
price_tier["analytic_type"] = "price_tier_time"
fa_chunks.append(price_tier)

# ── KPI tổng hợp
kpi_df = pd.DataFrame([{
    "chi_so": k, "gia_tri": v, "analytic_type": "kpi_summary"
} for k, v in {
    "tong_doanh_thu_vnd":   fact["line_total"].sum(),
    "tong_doanh_thu_ty":    round(fact["line_total"].sum()/1e9,2),
    "tong_san_luong":       int(fact["quantity"].sum()),
    "tong_don_hang":        fact["so_number"].nunique(),
    "tong_dai_ly":          fact["customer_code"].nunique(),
    "tong_sku":             fact["product_code"].nunique(),
    "tong_tinh":            fact["province_name"].dropna().nunique(),
    "gia_ban_tb":           round(fact["line_total"].sum()/fact["quantity"].sum(),0),
    "dt_tb_dai_ly":         round(fact["line_total"].sum()/fact["customer_code"].nunique(),0),
    "dt_tb_don":            round(fact["line_total"].sum()/fact["so_number"].nunique(),0),
    "ngay_bat_dau":         str(fact["order_date"].min().date()),
    "ngay_ket_thuc":        str(fact["order_date"].max().date()),
    "so_thang":             fact["ym"].nunique(),
}.items()])
fa_chunks.append(kpi_df)

fa_all = pd.concat(fa_chunks, ignore_index=True)
save(fa_all.sort_values(["analytic_type"], na_position="last"),
     "05_forecast_analytics.csv")

# ─────────────────────────────────────────────────────────────────────────────
print(f"""
{'='*65}
✅  HOÀN THÀNH — 5 file CSV siêu lớn
{'='*65}""")
for f in sorted(OUT.glob("*.csv")):
    rows = sum(1 for _ in open(f, encoding="utf-8-sig")) - 1
    size_kb = f.stat().st_size // 1024
    print(f"  {f.name:<45} {rows:>8,} dòng  {size_kb:>6,} KB")
print("="*65)
