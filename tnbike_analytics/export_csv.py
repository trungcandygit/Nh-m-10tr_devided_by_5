"""
export_csv.py — Tách toàn bộ dữ liệu thành nhiều CSV chuyên dụng

output/
├── data/                         # Dữ liệu thực tế (không có dự báo / ML output)
│   ├── raw_history.csv           # Lịch sử Q1-2025 + Q1-2026 (từ SQL)      17,031 rows
│   ├── raw_t3_orders.csv         # T3/2026 từ email/PDF pipeline              8,559 rows
│   ├── kpi_overview.csv          # 12 KPI tổng hợp                              12 rows
│   ├── monthly_trend.csv         # Tháng × nhóm SP: DT, SL, YoY, MoM, YTD     36 rows
│   ├── product_analysis.csv      # SKU: Pareto A/B/C, BCG, YoY                161 rows
│   ├── color_analysis.csv        # Màu × nhóm × tháng                         328 rows
│   ├── color_history.csv         # Lịch sử tỷ trọng màu theo tháng            329 rows
│   ├── dealer_rfm.csv            # Đại lý: RFM features & segments             333 rows
│   ├── geo_province.csv          # Tỉnh thành: DT, rank, share                  74 rows
│   ├── geo_region.csv            # Vùng × nhóm SP                               20 rows
│   ├── ops_pipeline.csv          # Thống kê pipeline email T3                    8 rows
│   └── ops_daily.csv             # DT + đơn mỗi ngày T3                         31 rows
│
└── prediction/                   # Dữ liệu dự báo & ML output
    ├── revenue_q2_daily.csv      # Prophet: dự báo doanh thu daily Q2        1,041 rows
    ├── revenue_q2_monthly.csv    # Prophet: tháng × nhóm SP                     49 rows
    ├── revenue_q2_weekly.csv     # Prophet: tuần × nhóm SP (Q2 only)            ~78 rows
    ├── sku_q2_forecast.csv       # Top-20 SKU dự báo bán chạy Q2               ~500 rows
    ├── color_q2.csv              # Màu × nhóm × tháng Q2 + seasonal_trend      183 rows
    ├── sku_cluster.csv           # K-Means cluster + slow_mover_risk            161 rows
    ├── dealer_churn.csv          # LightGBM: P(churn), nhãn, SHAP              333 rows
    ├── dealer_activity.csv       # BG-NBD: prob_purchase_30d + RFM + priority   333 rows
    └── shap_importance.csv       # SHAP feature importance ranking                9 rows
"""

import csv, sys, warnings, logging
import numpy as np
import pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("export_csv")

sys.path.insert(0, str(Path(__file__).parent))
from analytics.sql_data_loader import load_all, build_fact
from analytics.t3_loader import load_t3

OUT_DATA = Path(__file__).parent / "output" / "data"
OUT_PRED = Path(__file__).parent / "output" / "prediction"
for p in [OUT_DATA, OUT_PRED]:
    p.mkdir(parents=True, exist_ok=True)

QW = dict(index=False, encoding="utf-8-sig", quoting=csv.QUOTE_NONNUMERIC)

# ══════════════════════════════════════════════════
# LOAD
# ══════════════════════════════════════════════════
log.info("Loading data...")
dfs  = load_all()
fact_hist = build_fact(dfs)
fact_hist["order_date"]   = pd.to_datetime(fact_hist["order_date"])
fact_hist["product_code"] = fact_hist["product_code"].astype(str)
fact_hist["ym"]           = fact_hist["order_date"].dt.to_period("M").astype(str)

t3 = load_t3(dfs)

fact = pd.concat([fact_hist, t3], ignore_index=True) if not t3.empty else fact_hist.copy()
fact["order_date"]   = pd.to_datetime(fact["order_date"])
fact["product_code"] = fact["product_code"].astype(str)
fact["ym"]           = fact["order_date"].dt.to_period("M").astype(str)

FEAT_END = pd.Timestamp("2025-03-31")

# ══════════════════════════════════════════════════
# DATA/ — Dữ liệu thực tế (không dự báo)
# ══════════════════════════════════════════════════
log.info("=== DATA/ ===")

# ── raw_history.csv ───────────────────────────────────
raw_hist = fact_hist[[
    "so_number","order_date","fiscal_year","fiscal_month","fiscal_quarter",
    "customer_code","customer_name","province_name","region",
    "product_code","product_name","color","line_name","group_code","group_name",
    "quantity","unit_price","line_total",
]].copy()
raw_hist.to_csv(OUT_DATA / "raw_history.csv", **QW)
log.info(f"  raw_history.csv          {len(raw_hist):>7,} rows")

# ── raw_t3_orders.csv ───────────────────────────────
T3_COLS = ["so_number","order_date","fiscal_year","fiscal_month","fiscal_quarter",
           "customer_code","customer_name","province_name","region",
           "product_code","product_name","color","line_name","group_code","group_name",
           "quantity","unit_price","line_total"]
if t3.empty or not all(c in t3.columns for c in T3_COLS):
    raw_t3 = pd.DataFrame(columns=T3_COLS)
else:
    raw_t3 = t3[T3_COLS].copy()
raw_t3.to_csv(OUT_DATA / "raw_t3_orders.csv", **QW)
log.info(f"  raw_t3_orders.csv        {len(raw_t3):>7,} rows  ({raw_t3['so_number'].nunique() if not raw_t3.empty else 0} orders)")

# ── kpi_overview.csv ──────────────────────────────────
nat_rev  = int(fact["line_total"].sum())
hist_rev = int(fact_hist["line_total"].sum())
t3_rev   = int(t3["line_total"].sum()) if not t3.empty else 0

kpi = pd.DataFrame([
    {"kpi":"total_revenue",        "value":nat_rev,                                          "unit":"VND",    "period":"Jan2025-Mar2026"},
    {"kpi":"revenue_history",      "value":hist_rev,                                         "unit":"VND",    "period":"Jan2025-Feb2026"},
    {"kpi":"revenue_t3",           "value":t3_rev,                                           "unit":"VND",    "period":"Mar2026"},
    {"kpi":"total_orders",         "value":fact["so_number"].nunique(),                      "unit":"đơn",    "period":"Jan2025-Mar2026"},
    {"kpi":"total_order_lines",    "value":len(fact),                                        "unit":"dòng",   "period":"Jan2025-Mar2026"},
    {"kpi":"active_dealers",       "value":fact["customer_code"].nunique(),                  "unit":"đại lý", "period":"Jan2025-Mar2026"},
    {"kpi":"total_quantity",       "value":int(fact["quantity"].sum()),                      "unit":"chiếc",  "period":"Jan2025-Mar2026"},
    {"kpi":"avg_order_value",      "value":int(fact.groupby("so_number")["line_total"].sum().mean()), "unit":"VND","period":"Jan2025-Mar2026"},
    {"kpi":"sku_count",            "value":fact["product_code"].nunique(),                   "unit":"SKU",    "period":"Jan2025-Mar2026"},
    {"kpi":"t3_orders_processed",  "value":raw_t3["so_number"].nunique(),                   "unit":"đơn",    "period":"Mar2026"},
    {"kpi":"t3_orders_failed",     "value":1132-raw_t3["so_number"].nunique(),               "unit":"đơn",    "period":"Mar2026"},
    {"kpi":"t3_success_rate",      "value":round(raw_t3["so_number"].nunique()/1132*100,1), "unit":"%",      "period":"Mar2026"},
])
kpi.to_csv(OUT_DATA / "kpi_overview.csv", **QW)
log.info(f"  kpi_overview.csv            {len(kpi):>3} rows")

# ── monthly_trend.csv ─────────────────────────────────
monthly = (fact.groupby(["fiscal_year","fiscal_month","fiscal_quarter","ym","group_code","group_name"])
           .agg(revenue=("line_total","sum"), quantity=("quantity","sum"),
                n_orders=("so_number","nunique"), n_customers=("customer_code","nunique"))
           .reset_index())
monthly_total = (fact.groupby(["fiscal_year","fiscal_month","fiscal_quarter","ym"])
                 .agg(revenue=("line_total","sum"), quantity=("quantity","sum"),
                      n_orders=("so_number","nunique"), n_customers=("customer_code","nunique"))
                 .reset_index())
monthly_total["group_code"] = "__ALL__"
monthly_total["group_name"] = "Tất cả nhóm"
monthly = pd.concat([monthly, monthly_total], ignore_index=True)

base25 = monthly[monthly.fiscal_year==2025][["fiscal_month","group_code","revenue"]].rename(columns={"revenue":"_r25"})
monthly = monthly.merge(base25, on=["fiscal_month","group_code"], how="left")
monthly["yoy_revenue_pct"] = ((monthly["revenue"]-monthly["_r25"])/monthly["_r25"].replace(0,np.nan)*100).round(2)
monthly.loc[monthly.fiscal_year==2025, "yoy_revenue_pct"] = np.nan
monthly.drop(columns=["_r25"], inplace=True)
monthly = monthly.sort_values(["group_code","fiscal_year","fiscal_month"])
monthly["mom_revenue_pct"]  = (monthly.groupby("group_code")["revenue"].pct_change()*100).round(2)
monthly["cum_revenue_ytd"]  = monthly.groupby(["group_code","fiscal_year"])["revenue"].cumsum()

monthly.to_csv(OUT_DATA / "monthly_trend.csv", **QW)
log.info(f"  monthly_trend.csv           {len(monthly):>3} rows")

# ── product_analysis.csv ────────────────────────────────
sku = (fact.groupby(["product_code","product_name","color","line_name","group_code","group_name"])
       .agg(revenue=("line_total","sum"), quantity=("quantity","sum"),
            n_orders=("so_number","nunique"), n_customers=("customer_code","nunique"))
       .reset_index())

for yr in [2025, 2026]:
    sub = fact[fact.fiscal_year==yr].groupby("product_code").agg(
        **{f"rev_{yr}":("line_total","sum"), f"qty_{yr}":("quantity","sum")}).reset_index()
    sku = sku.merge(sub, on="product_code", how="left")
for c in ["rev_2025","rev_2026","qty_2025","qty_2026"]:
    sku[c] = sku[c].fillna(0)

sku["rev_2026_ann"] = sku["rev_2026"] * 4
sku["yoy_rev_pct"]  = ((sku["rev_2026_ann"]-sku["rev_2025"])/sku["rev_2025"].replace(0,np.nan)*100).round(2)
sku["avg_unit_price"] = (sku["revenue"]/sku["quantity"].replace(0,np.nan)).round(0).fillna(0)
sku = sku.sort_values("revenue", ascending=False).reset_index(drop=True)
sku["revenue_rank"]   = range(1, len(sku)+1)
sku["pareto_cum_pct"] = (sku["revenue"].cumsum()/sku["revenue"].sum()*100).round(2)
sku["pareto_class"]   = pd.cut(sku["pareto_cum_pct"], bins=[0,70,90,100], labels=["A","B","C"])
grp_rev = sku.groupby("group_code")["revenue"].sum()
sku["rev_share_in_group_pct"] = (sku["revenue"]/sku["group_code"].map(grp_rev)*100).round(2)

bcg_parts = []
for gc, g in sku.groupby("group_code"):
    g = g.copy()
    ms = g["rev_share_in_group_pct"].median()
    mg = g["yoy_rev_pct"].median()
    def _q(r):
        hs = r.rev_share_in_group_pct >= ms
        hg = (r.yoy_rev_pct >= mg) if pd.notna(r.yoy_rev_pct) else False
        if hs and hg: return "Ngôi sao"
        if hs:        return "Bò sữa"
        if hg:        return "Dấu hỏi"
        return "Con chó"
    g["bcg_quadrant"] = g.apply(_q, axis=1)
    bcg_parts.append(g)
sku = pd.concat(bcg_parts, ignore_index=True)

sku.to_csv(OUT_DATA / "product_analysis.csv", **QW)
log.info(f"  product_analysis.csv       {len(sku):>4} rows")

# ── color_analysis.csv ─────────────────────────────────
color_agg = (fact.groupby(["color","group_code","group_name","fiscal_year","fiscal_month"])
             .agg(revenue=("line_total","sum"), quantity=("quantity","sum"),
                  n_orders=("so_number","nunique"))
             .reset_index())
color_agg["ym"] = color_agg.apply(lambda r: f"{int(r.fiscal_year)}-{int(r.fiscal_month):02d}", axis=1)
color_agg.to_csv(OUT_DATA / "color_analysis.csv", **QW)
log.info(f"  color_analysis.csv         {len(color_agg):>4} rows")

# ── color_history.csv (tỷ trọng màu theo tháng) ─────
color_hist = (fact.groupby(["color","group_code","fiscal_year","fiscal_month"])
              .agg(revenue=("line_total","sum"), quantity=("quantity","sum"))
              .reset_index())
color_hist["ym"] = color_hist.apply(lambda r: f"{int(r.fiscal_year)}-{int(r.fiscal_month):02d}", axis=1)
color_total = color_hist.groupby(["fiscal_year","fiscal_month"])["revenue"].sum().rename("_tot")
color_hist  = color_hist.merge(color_total, on=["fiscal_year","fiscal_month"], how="left")
color_hist["color_share_pct"] = (color_hist["revenue"]/color_hist["_tot"]*100).round(2)
color_hist.drop(columns=["_tot"], inplace=True)
color_hist.to_csv(OUT_DATA / "color_history.csv", **QW)
log.info(f"  color_history.csv          {len(color_hist):>4} rows")

# ── dealer_rfm.csv — lấy từ prediction_engine (RFM only, không churn) ──
from analytics.prediction_engine import run_q1_forecast, run_q2_color_demand, run_q3_dealer_forecast

log.info("  Đang tính dealer RFM (dùng cho data/)...")
q3_out = run_q3_dealer_forecast(fact)
dealer_act = q3_out["dealer_activity"]

rfm_cols = [
    "customer_code","customer_name","province_name","region",
    "cohort_month","first_order_date","last_order_q1_2025",
    "recency_days","n_orders_q1_2025","revenue_q1_2025",
    "avg_order_value","n_product_groups","trend_slope","groups_bought",
    "n_orders_q1_2026","revenue_q1_2026","churn_label",
    "rfm_r","rfm_f","rfm_m","rfm_segment",
]
# Chỉ lưu các cột tồn tại trong dealer_act
rfm_save = [c for c in rfm_cols if c in dealer_act.columns]
dealer_act[rfm_save].to_csv(OUT_DATA / "dealer_rfm.csv", **QW)
log.info(f"  dealer_rfm.csv             {len(dealer_act):>4} rows")

# ── geo_province.csv & geo_region.csv ───────────────────
nat_rev_total = int(fact["line_total"].sum())
prov = (fact.groupby(["province_name","region"])
        .agg(revenue=("line_total","sum"), quantity=("quantity","sum"),
             n_orders=("so_number","nunique"), n_customers=("customer_code","nunique"))
        .reset_index())
reg_rev = prov.groupby("region")["revenue"].sum().rename("_reg")
prov = prov.merge(reg_rev, on="region", how="left")
prov["rev_pct_national"] = (prov["revenue"]/nat_rev_total*100).round(2)
prov["rev_pct_region"]   = (prov["revenue"]/prov["_reg"]*100).round(2)
prov.drop(columns=["_reg"], inplace=True)
prov["rank_national"]  = prov["revenue"].rank(ascending=False, method="dense").astype(int)
prov["rank_in_region"] = prov.groupby("region")["revenue"].rank(ascending=False, method="dense").astype(int)

region = (fact.groupby(["region","group_code","group_name"])
          .agg(revenue=("line_total","sum"), quantity=("quantity","sum"),
               n_orders=("so_number","nunique"), n_customers=("customer_code","nunique"))
          .reset_index())

prov.to_csv(OUT_DATA / "geo_province.csv", **QW)
region.to_csv(OUT_DATA / "geo_region.csv", **QW)
log.info(f"  geo_province.csv            {len(prov):>3} rows")
log.info(f"  geo_region.csv              {len(region):>3} rows")

# ── ops_pipeline.csv & ops_daily.csv ────────────────────
ops = pd.DataFrame([
    {"metric":"tong_email_nhan",      "value":1132,                               "mo_ta":"Tổng email nhận T3/2026"},
    {"metric":"don_xu_ly_thanh_cong", "value":raw_t3["so_number"].nunique(),       "mo_ta":"Đơn xử lý thành công"},
    {"metric":"don_loi_parse",        "value":1132-raw_t3["so_number"].nunique(),  "mo_ta":"Đơn lỗi/không parse được"},
    {"metric":"ty_le_thanh_cong_pct", "value":round(raw_t3["so_number"].nunique()/1132*100,1), "mo_ta":"Tỷ lệ thành công (%)"},
    {"metric":"tong_dong_sp",         "value":len(raw_t3),                         "mo_ta":"Tổng dòng sản phẩm T3"},
    {"metric":"doanh_thu_t3",         "value":int(raw_t3["line_total"].sum()) if not raw_t3.empty else 0, "mo_ta":"Doanh thu T3/2026 (VND)"},
    {"metric":"so_dai_ly_t3",         "value":raw_t3["customer_code"].nunique(),    "mo_ta":"Số đại lý đặt hàng T3"},
    {"metric":"phuong_an",            "value":"A",                                  "mo_ta":"Email + PDF (tối đa 25đ)"},
])
t3_by_day = raw_t3.groupby("order_date").agg(
    n_orders=("so_number","nunique"), revenue=("line_total","sum")).reset_index()
t3_by_day["order_date"] = t3_by_day["order_date"].astype(str)

ops.to_csv(OUT_DATA / "ops_pipeline.csv", **QW)
t3_by_day.to_csv(OUT_DATA / "ops_daily.csv", **QW)
log.info(f"  ops_pipeline.csv              {len(ops):>2} rows")
log.info(f"  ops_daily.csv                 {len(t3_by_day):>2} rows")

# ══════════════════════════════════════════════════
# PREDICTION/ — Q1 + Q2 + Q3 qua prediction_engine
# ══════════════════════════════════════════════════
log.info("=== PREDICTION/ ===")

# ── Q1: Prophet forecast ──────────────────────────────────
log.info("  [Q1] Chạy Prophet forecast...")
q1_out = run_q1_forecast(fact)

q1_out["daily"].to_csv(OUT_PRED / "revenue_q2_daily.csv", **QW)
log.info(f"  revenue_q2_daily.csv     {len(q1_out['daily']):>6,} rows")

q1_out["monthly"].to_csv(OUT_PRED / "revenue_q2_monthly.csv", **QW)
log.info(f"  revenue_q2_monthly.csv      {len(q1_out['monthly']):>4} rows")

q1_out["weekly"].to_csv(OUT_PRED / "revenue_q2_weekly.csv", **QW)
log.info(f"  revenue_q2_weekly.csv       {len(q1_out['weekly']):>4} rows")

q1_out["sku_q2"].to_csv(OUT_PRED / "sku_q2_forecast.csv", **QW)
top20 = q1_out["sku_q2"]["top20_flag"].sum() if "top20_flag" in q1_out["sku_q2"].columns else "?"
log.info(f"  sku_q2_forecast.csv        {len(q1_out['sku_q2']):>4} rows  (top20: {top20})")

# ── Q2: Color demand + K-Means slow-mover ─────────────────
log.info("  [Q2] Chạy color demand + K-Means...")
q2_out = run_q2_color_demand(fact, q1_out["monthly"])

q2_out["color_history"].to_csv(OUT_DATA / "color_history.csv", **QW)
log.info(f"  color_history.csv (update)  {len(q2_out['color_history']):>4} rows")

q2_out["color_q2"].to_csv(OUT_PRED / "color_q2.csv", **QW)
log.info(f"  color_q2.csv               {len(q2_out['color_q2']):>4} rows")

q2_out["sku_cluster"].to_csv(OUT_PRED / "sku_cluster.csv", **QW)
slow = (q2_out["sku_cluster"]["slow_mover_risk"] == "Nguy cơ cao").sum()
log.info(f"  sku_cluster.csv            {len(q2_out['sku_cluster']):>4} rows  (slow-mover: {slow})")

# ── Q3: BG-NBD + LightGBM + SHAP ──────────────────────
# (q3_out đã chạy ở trên khi build dealer_rfm.csv)
q3_out["dealer_churn"].to_csv(OUT_PRED / "dealer_churn.csv", **QW)
log.info(f"  dealer_churn.csv           {len(q3_out['dealer_churn']):>4} rows")

# dealer_activity: lưu toàn bộ cột cần cho dashboard
act_cols = [
    "customer_code","customer_name","province_name","region",
    "recency_days","n_orders_q1_2025","revenue_q1_2025",
    "avg_order_value","n_product_groups","trend_slope","groups_bought",
    "n_orders_q1_2026","revenue_q1_2026","churn_label",
    "rfm_r","rfm_f","rfm_m","rfm_segment",
    "prob_purchase_30d","expected_orders_30d","activity_risk","priority_contact",
    "trend_score","marketing_priority","marketing_priority_label",
]
act_save = [c for c in act_cols if c in dealer_act.columns]
dealer_act[act_save].to_csv(OUT_PRED / "dealer_activity.csv", **QW)
log.info(f"  dealer_activity.csv        {len(dealer_act):>4} rows")

q3_out["shap_importance"].to_csv(OUT_PRED / "shap_importance.csv", **QW)
log.info(f"  shap_importance.csv          {len(q3_out['shap_importance']):>2} rows")

# ══════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════
log.info("─"*60)
log.info("✓ Xong! Tất cả CSV:")
for d in [OUT_DATA, OUT_PRED]:
    label = "data/" if "data" in d.name else "prediction/"
    for fp in sorted(d.glob("*.csv")):
        rows = sum(1 for _ in open(fp, encoding="utf-8-sig")) - 1
        kb   = fp.stat().st_size // 1024
        log.info(f"  output/{label}{fp.name:<35} {rows:>6,} rows  {kb:>4}KB")
