"""
export_csv.py — Tách toàn bộ dữ liệu thành nhiều CSV chuyên dụng

output/
├── data/                     # Dữ liệu thô
│   ├── raw_history.csv       # Lịch sử Q1-2025 + Q1-2026 (từ DB)
│   └── raw_t3_orders.csv     # T3/2026 từ email/PDF
│
├── dashboard/                # Sẵn cho 6 màn hình dashboard
│   ├── 01_kpi_overview.csv
│   ├── 02_monthly_trend.csv
│   ├── 03_product_analysis.csv
│   ├── 04_dealer_rfm.csv
│   ├── 05_geo_analysis.csv
│   └── 06_ops_pipeline.csv
│
└── forecast/                 # Hạng mục C — Dự báo nhu cầu Q2/2026
    ├── c1_revenue_q2.csv     # Câu 1: Dự báo doanh số theo tháng × nhóm
    ├── c2_color_q2.csv       # Câu 2: Dự báo màu sắc
    └── c3_dealer_activity.csv # Câu 3: Dự báo hoạt động đại lý
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

OUT_DATA  = Path(__file__).parent / "output" / "data"
OUT_DASH  = Path(__file__).parent / "output" / "dashboard"
OUT_FCST  = Path(__file__).parent / "output" / "forecast"
for p in [OUT_DATA, OUT_DASH, OUT_FCST]:
    p.mkdir(parents=True, exist_ok=True)

QW = dict(index=False, encoding="utf-8-sig", quoting=csv.QUOTE_NONNUMERIC)

# ════════════════════════════════════════════════════
# LOAD
# ════════════════════════════════════════════════════
log.info("Loading data...")
dfs  = load_all()
fact_hist = build_fact(dfs)
fact_hist["order_date"]   = pd.to_datetime(fact_hist["order_date"])
fact_hist["product_code"] = fact_hist["product_code"].astype(str)
fact_hist["ym"]           = fact_hist["order_date"].dt.to_period("M").astype(str)

t3 = load_t3(dfs)

fact = pd.concat([fact_hist, t3], ignore_index=True)
fact["order_date"]   = pd.to_datetime(fact["order_date"])
fact["product_code"] = fact["product_code"].astype(str)
fact["ym"]           = fact["order_date"].dt.to_period("M").astype(str)

FEAT_END = pd.Timestamp("2025-03-31")

# ════════════════════════════════════════════════════
# DATA/ — Dữ liệu thô
# ════════════════════════════════════════════════════
log.info("=== DATA/ ===")

# 1. raw_history.csv
raw_hist = fact_hist[[
    "so_number","order_date","fiscal_year","fiscal_month","fiscal_quarter",
    "customer_code","customer_name","province_name","region",
    "product_code","product_name","color","line_name","group_code","group_name",
    "quantity","unit_price","line_total",
]].copy()
raw_hist.to_csv(OUT_DATA / "raw_history.csv", **QW)
log.info(f"  raw_history.csv       {len(raw_hist):>7,} rows")

# 2. raw_t3_orders.csv
raw_t3 = t3[[
    "so_number","order_date","fiscal_year","fiscal_month","fiscal_quarter",
    "customer_code","customer_name","province_name","region",
    "product_code","product_name","color","line_name","group_code","group_name",
    "quantity","unit_price","line_total",
]].copy()
raw_t3.to_csv(OUT_DATA / "raw_t3_orders.csv", **QW)
log.info(f"  raw_t3_orders.csv     {len(raw_t3):>7,} rows  ({raw_t3['so_number'].nunique()} orders)")

# ════════════════════════════════════════════════════
# DASHBOARD/ — 6 màn hình
# ════════════════════════════════════════════════════
log.info("=== DASHBOARD/ ===")

# ── Màn hình 1: KPI Tổng quan ──────────────────────
nat_rev   = int(fact["line_total"].sum())
hist_rev  = int(fact_hist["line_total"].sum())
t3_rev    = int(t3["line_total"].sum()) if not t3.empty else 0

kpi = pd.DataFrame([
    {"kpi":"total_revenue",         "value":nat_rev,                            "unit":"VND",    "period":"Jan2025-Mar2026"},
    {"kpi":"revenue_history",       "value":hist_rev,                           "unit":"VND",    "period":"Jan2025-Feb2026"},
    {"kpi":"revenue_t3",            "value":t3_rev,                             "unit":"VND",    "period":"Mar2026"},
    {"kpi":"total_orders",          "value":fact["so_number"].nunique(),         "unit":"đơn",    "period":"Jan2025-Mar2026"},
    {"kpi":"total_order_lines",     "value":len(fact),                          "unit":"dòng",   "period":"Jan2025-Mar2026"},
    {"kpi":"active_dealers",        "value":fact["customer_code"].nunique(),     "unit":"đại lý", "period":"Jan2025-Mar2026"},
    {"kpi":"total_quantity",        "value":int(fact["quantity"].sum()),         "unit":"chiếc",  "period":"Jan2025-Mar2026"},
    {"kpi":"avg_order_value",       "value":int(fact.groupby("so_number")["line_total"].sum().mean()), "unit":"VND","period":"Jan2025-Mar2026"},
    {"kpi":"sku_count",             "value":fact["product_code"].nunique(),      "unit":"SKU",    "period":"Jan2025-Mar2026"},
    {"kpi":"t3_orders_processed",   "value":raw_t3["so_number"].nunique(),      "unit":"đơn",    "period":"Mar2026"},
    {"kpi":"t3_orders_failed",      "value":1132-raw_t3["so_number"].nunique(), "unit":"đơn",    "period":"Mar2026"},
    {"kpi":"t3_success_rate",       "value":round(raw_t3["so_number"].nunique()/1132*100,1), "unit":"%","period":"Mar2026"},
])
kpi.to_csv(OUT_DASH / "01_kpi_overview.csv", **QW)
log.info(f"  01_kpi_overview.csv      {len(kpi):>4} rows")

# ── Màn hình 2: Phân tích thời gian ────────────────
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

# YoY
base25 = monthly[monthly.fiscal_year==2025][["fiscal_month","group_code","revenue"]].rename(columns={"revenue":"_r25"})
monthly = monthly.merge(base25, on=["fiscal_month","group_code"], how="left")
monthly["yoy_revenue_pct"] = ((monthly["revenue"]-monthly["_r25"])/monthly["_r25"].replace(0,np.nan)*100).round(2)
monthly.loc[monthly.fiscal_year==2025, "yoy_revenue_pct"] = np.nan
monthly.drop(columns=["_r25"], inplace=True)

# MoM
monthly = monthly.sort_values(["group_code","fiscal_year","fiscal_month"])
monthly["mom_revenue_pct"] = (monthly.groupby("group_code")["revenue"].pct_change()*100).round(2)

# YTD
monthly["cum_revenue_ytd"] = monthly.groupby(["group_code","fiscal_year"])["revenue"].cumsum()

monthly.to_csv(OUT_DASH / "02_monthly_trend.csv", **QW)
log.info(f"  02_monthly_trend.csv     {len(monthly):>4} rows")

# ── Màn hình 3: Phân tích sản phẩm ─────────────────
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

sku["rev_2026_ann"] = sku["rev_2026"] * 4   # annualize (3 tháng → 12)
sku["yoy_rev_pct"]  = ((sku["rev_2026_ann"]-sku["rev_2025"])/sku["rev_2025"].replace(0,np.nan)*100).round(2)
sku["avg_unit_price"] = (sku["revenue"]/sku["quantity"].replace(0,np.nan)).round(0).fillna(0)
sku = sku.sort_values("revenue", ascending=False).reset_index(drop=True)
sku["revenue_rank"]   = range(1, len(sku)+1)
sku["pareto_cum_pct"] = (sku["revenue"].cumsum()/sku["revenue"].sum()*100).round(2)
sku["pareto_class"]   = pd.cut(sku["pareto_cum_pct"], bins=[0,70,90,100], labels=["A","B","C"])

grp_rev = sku.groupby("group_code")["revenue"].sum()
sku["rev_share_in_group_pct"] = (sku["revenue"]/sku["group_code"].map(grp_rev)*100).round(2)

# BCG
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

# Color analysis
color_agg = (fact.groupby(["color","group_code","group_name","fiscal_year","fiscal_month"])
             .agg(revenue=("line_total","sum"), quantity=("quantity","sum"),
                  n_orders=("so_number","nunique"))
             .reset_index())
color_agg["ym"] = color_agg.apply(lambda r: f"{int(r.fiscal_year)}-{int(r.fiscal_month):02d}", axis=1)

sku.to_csv(OUT_DASH / "03_product_analysis.csv", **QW)
color_agg.to_csv(OUT_DASH / "03_color_analysis.csv", **QW)
log.info(f"  03_product_analysis.csv  {len(sku):>4} rows")
log.info(f"  03_color_analysis.csv    {len(color_agg):>4} rows")

# ── Màn hình 4: Phân tích đại lý ───────────────────
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.metrics import roc_auc_score

q1_2025 = fact[fact.order_date <= FEAT_END]
active_2026 = set(fact[fact.order_date >= "2026-01-01"]["customer_code"].unique())
cust_meta = (fact[["customer_code","customer_name","province_name","region"]]
             .drop_duplicates("customer_code").set_index("customer_code"))

feats = []
for cc, g in q1_2025.groupby("customer_code"):
    g = g.sort_values("order_date")
    last = g["order_date"].max()
    monthly_rev = g.groupby(g["order_date"].dt.to_period("M"))["line_total"].sum()
    slope = 0.0
    if len(monthly_rev) >= 2:
        slope = float(np.polyfit(np.arange(len(monthly_rev)), monthly_rev.values, 1)[0])
    m = cust_meta.loc[cc] if cc in cust_meta.index else {}
    q_orders = fact[(fact.customer_code==cc) & (fact.order_date >= "2026-01-01")]["so_number"].nunique()
    feats.append({
        "customer_code":     cc,
        "customer_name":     m.get("customer_name",""),
        "province_name":     m.get("province_name",""),
        "region":            m.get("region",""),
        "cohort_month":      g["order_date"].min().strftime("%Y-%m"),
        "first_order_date":  g["order_date"].min().date(),
        "last_order_q1_2025":last.date(),
        "recency_days":      (FEAT_END - last).days,
        "n_orders_q1_2025":  g["so_number"].nunique(),
        "revenue_q1_2025":   int(g["line_total"].sum()),
        "avg_order_value":   round(g.groupby("so_number")["line_total"].sum().mean(),0),
        "n_product_groups":  g["group_code"].nunique(),
        "trend_slope":       round(slope,2),
        "groups_bought":     "|".join(sorted(g["group_code"].dropna().unique())),
        "n_orders_q1_2026":  q_orders,
        "revenue_q1_2026":   int(fact[(fact.customer_code==cc)&(fact.order_date>="2026-01-01")]["line_total"].sum()),
    })

cdf = pd.DataFrame(feats)
cdf["churn_label"] = (~cdf["customer_code"].isin(active_2026)).astype(int)

for col, sc, asc in [("recency_days","rfm_r",True),("n_orders_q1_2025","rfm_f",False),("revenue_q1_2025","rfm_m",False)]:
    rk = cdf[col].rank(pct=True, method="average")
    bins, labels = [0,.2,.4,.6,.8,1.0], ([5,4,3,2,1] if asc else [1,2,3,4,5])
    cdf[sc] = pd.cut(rk, bins=bins, labels=labels, include_lowest=True).astype(int)

def rfm_seg(r,f,m):
    if r>=4 and f>=4 and m>=4: return "Khách hàng tiêu biểu"
    if r>=4 and f>=3:           return "Khách hàng trung thành"
    if r>=4:                    return "Khách hàng mới tiềm năng"
    if r<=2 and f>=4:           return "Cần chăm sóc đặc biệt"
    if r<=2:                    return "Có nguy cơ rời bỏ"
    return "Cần theo dõi"
cdf["rfm_segment"] = cdf.apply(lambda r: rfm_seg(r.rfm_r, r.rfm_f, r.rfm_m), axis=1)

X_cols = ["recency_days","n_orders_q1_2025","revenue_q1_2025","avg_order_value","n_product_groups","trend_slope"]
X = cdf[X_cols].fillna(0).values
y = cdf["churn_label"].values
sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
tr_idx, te_idx = next(sss.split(X, y))
pipe = Pipeline([("sc",StandardScaler()),("cl",LogisticRegression(C=1.0,max_iter=1000,random_state=42))])
pipe.fit(X[tr_idx], y[tr_idx])
cdf["churn_prob"]     = pipe.predict_proba(X)[:,1].round(4)
cdf["churn_split"]    = "train"
cdf.loc[cdf.index[te_idx], "churn_split"] = "test"
cdf["churn_priority"] = pd.cut(cdf["churn_prob"], bins=[0,.3,.6,1.0],
                                labels=["Thấp","Trung bình","Cao"], include_lowest=True)
roc_te = roc_auc_score(y[te_idx], pipe.predict_proba(X[te_idx])[:,1])
cdf["roc_auc_test"] = round(roc_te, 4)
log.info(f"   Churn model ROC-AUC test: {roc_te:.3f}")

cdf.to_csv(OUT_DASH / "04_dealer_rfm.csv", **QW)
log.info(f"  04_dealer_rfm.csv        {len(cdf):>4} rows")

# ── Màn hình 5: Địa lý ─────────────────────────────
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
prov["rank_national"] = prov["revenue"].rank(ascending=False, method="dense").astype(int)
prov["rank_in_region"] = prov.groupby("region")["revenue"].rank(ascending=False, method="dense").astype(int)

region = (fact.groupby(["region","group_code","group_name"])
          .agg(revenue=("line_total","sum"), quantity=("quantity","sum"),
               n_orders=("so_number","nunique"), n_customers=("customer_code","nunique"))
          .reset_index())

prov.to_csv(OUT_DASH / "05_geo_province.csv", **QW)
region.to_csv(OUT_DASH / "05_geo_region.csv", **QW)
log.info(f"  05_geo_province.csv      {len(prov):>4} rows")
log.info(f"  05_geo_region.csv        {len(region):>4} rows")

# ── Màn hình 6: Trạng thái vận hành ─────────────────
ops = pd.DataFrame([
    {"metric":"tong_email_nhan",      "value":1132,  "mo_ta":"Tổng email nhận T3/2026"},
    {"metric":"don_xu_ly_thanh_cong", "value":raw_t3["so_number"].nunique(), "mo_ta":"Đơn xử lý thành công"},
    {"metric":"don_loi_parse",        "value":1132-raw_t3["so_number"].nunique(), "mo_ta":"Đơn lỗi/không parse được"},
    {"metric":"ty_le_thanh_cong_pct", "value":round(raw_t3["so_number"].nunique()/1132*100,1), "mo_ta":"Tỷ lệ thành công (%)"},
    {"metric":"tong_dong_sp",         "value":len(raw_t3), "mo_ta":"Tổng dòng sản phẩm T3"},
    {"metric":"doanh_thu_t3",         "value":int(raw_t3["line_total"].sum()), "mo_ta":"Doanh thu T3/2026 (VND)"},
    {"metric":"so_dai_ly_t3",         "value":raw_t3["customer_code"].nunique(), "mo_ta":"Số đại lý đặt hàng T3"},
    {"metric":"phuong_an",            "value":"A",   "mo_ta":"Email + PDF (tối đa 25đ)"},
])

t3_by_day = raw_t3.groupby("order_date").agg(
    n_orders=("so_number","nunique"), revenue=("line_total","sum")).reset_index()
t3_by_day["order_date"] = t3_by_day["order_date"].astype(str)

ops.to_csv(OUT_DASH / "06_ops_pipeline.csv", **QW)
t3_by_day.to_csv(OUT_DASH / "06_ops_daily.csv", **QW)
log.info(f"  06_ops_pipeline.csv        {len(ops):>2} rows")
log.info(f"  06_ops_daily.csv           {len(t3_by_day):>2} rows")

# ════════════════════════════════════════════════════
# FORECAST/ — Hạng mục C
# ════════════════════════════════════════════════════
log.info("=== FORECAST/ ===")

# ── C1: Dự báo doanh số Q2/2026 ────────────────────
forecast_rows = []
try:
    from prophet import Prophet
    TRAIN_END = pd.Timestamp("2026-03-31")
    FCST_END  = pd.Timestamp("2026-06-30")

    for gc in sorted(fact["group_code"].dropna().unique()):
        daily = (fact[fact.group_code==gc].groupby("order_date")["line_total"].sum()
                 .reset_index().rename(columns={"order_date":"ds","line_total":"y"}))
        daily["ds"] = pd.to_datetime(daily["ds"])
        train = daily[daily.ds <= TRAIN_END].copy()
        if len(train) < 10: continue
        cap = float(train["y"].max() * 2.5)
        train["cap"] = cap; train["floor"] = 0.0
        m = Prophet(growth="logistic", weekly_seasonality=True, daily_seasonality=False,
                    yearly_seasonality=False, seasonality_mode="multiplicative",
                    changepoint_prior_scale=0.10)
        m.add_country_holidays(country_name="VN")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m.fit(train)
        n_days = (FCST_END - train["ds"].max()).days
        fut = m.make_future_dataframe(periods=n_days)
        fut["cap"] = cap; fut["floor"] = 0.0
        fc = m.predict(fut)
        for col in ["yhat","yhat_lower","yhat_upper"]:
            fc[col] = fc[col].clip(lower=0)
        fc = fc[["ds","yhat","yhat_lower","yhat_upper"]].merge(
            daily.rename(columns={"y":"y_actual"}), on="ds", how="left")
        fc["y_actual"] = fc["y_actual"].fillna(0).astype(int)
        fc["split"] = "train"
        fc.loc[fc.ds > TRAIN_END, "split"] = "forecast"
        fc["group_code"] = gc
        fc["fiscal_month"] = fc["ds"].dt.month
        fc["fiscal_year"]  = fc["ds"].dt.year
        fc = fc[fc.ds > pd.Timestamp("2025-01-01")]
        forecast_rows.append(fc)
    log.info(f"   Prophet: {len(forecast_rows)} groups")
except ImportError:
    log.warning("   Prophet chưa cài")

if forecast_rows:
    fcst = pd.concat(forecast_rows, ignore_index=True)
    # Tổng hợp theo tháng × nhóm
    fcst_monthly = (fcst.groupby(["fiscal_year","fiscal_month","group_code","split"])
                    .agg(yhat=("yhat","sum"), yhat_lower=("yhat_lower","sum"),
                         yhat_upper=("yhat_upper","sum"), y_actual=("y_actual","sum"))
                    .reset_index())
    fcst_monthly["ym"] = fcst_monthly.apply(lambda r: f"{int(r.fiscal_year)}-{int(r.fiscal_month):02d}", axis=1)
    fcst["ds"] = fcst["ds"].astype(str)
    fcst.to_csv(OUT_FCST / "c1_revenue_q2_daily.csv", **QW)
    fcst_monthly.to_csv(OUT_FCST / "c1_revenue_q2_monthly.csv", **QW)
    log.info(f"  c1_revenue_q2_daily.csv   {len(fcst):>6,} rows")
    log.info(f"  c1_revenue_q2_monthly.csv {len(fcst_monthly):>4} rows")

# ── C2: Dự báo màu sắc Q2/2026 ─────────────────────
color_hist = (fact.groupby(["color","group_code","fiscal_year","fiscal_month"])
              .agg(revenue=("line_total","sum"), quantity=("quantity","sum"))
              .reset_index())
color_hist["ym"] = color_hist.apply(lambda r: f"{int(r.fiscal_year)}-{int(r.fiscal_month):02d}", axis=1)

# Share màu sắc theo tháng
color_total = color_hist.groupby(["fiscal_year","fiscal_month"])["revenue"].sum().rename("_tot")
color_hist = color_hist.merge(color_total, on=["fiscal_year","fiscal_month"], how="left")
color_hist["color_share_pct"] = (color_hist["revenue"]/color_hist["_tot"]*100).round(2)
color_hist.drop(columns=["_tot"], inplace=True)

# Dự báo đơn giản: trung bình tỷ trọng màu trong Q1-2026 → apply cho dự báo doanh số Q2
q1_2026_color_share = (
    color_hist[color_hist.fiscal_year==2026]
    .groupby(["color","group_code"])["color_share_pct"].mean().reset_index()
    .rename(columns={"color_share_pct":"avg_share_q1_2026_pct"}))

if forecast_rows:
    fcst_q2 = fcst_monthly[(fcst_monthly.fiscal_year==2026)&(fcst_monthly.fiscal_month.isin([4,5,6]))].copy()
    color_forecast = q1_2026_color_share.merge(
        fcst_q2[["fiscal_month","group_code","yhat","split"]].rename(columns={"yhat":"group_yhat"}),
        on="group_code", how="left")
    color_forecast["predicted_revenue"] = (color_forecast["avg_share_q1_2026_pct"]/100 * color_forecast["group_yhat"]).round(0)
    color_forecast.to_csv(OUT_FCST / "c2_color_q2.csv", **QW)
    log.info(f"  c2_color_q2.csv           {len(color_forecast):>4} rows")

color_hist.to_csv(OUT_FCST / "c2_color_history.csv", **QW)
log.info(f"  c2_color_history.csv      {len(color_hist):>4} rows")

# ── C3: Dự báo hoạt động đại lý ────────────────────
# Xác suất đặt hàng trong 30 ngày tới dựa trên LogReg churn model
REF_DATE = pd.Timestamp("2026-03-31")  # ngày tham chiếu

all_dealers = fact[["customer_code","customer_name","province_name","region"]].drop_duplicates("customer_code")
dealer_stats = []
for cc, g in fact.groupby("customer_code"):
    g = g.sort_values("order_date")
    last = g["order_date"].max()
    monthly_rev = g.groupby(g["order_date"].dt.to_period("M"))["line_total"].sum()
    slope = 0.0
    if len(monthly_rev) >= 2:
        slope = float(np.polyfit(np.arange(len(monthly_rev)), monthly_rev.values, 1)[0])
    dealer_stats.append({
        "customer_code":   cc,
        "last_order_date": last.date(),
        "recency_days":    (REF_DATE - last).days,
        "n_orders_total":  g["so_number"].nunique(),
        "revenue_total":   int(g["line_total"].sum()),
        "avg_order_value": round(g.groupby("so_number")["line_total"].sum().mean(),0),
        "n_product_groups":g["group_code"].nunique(),
        "trend_slope":     round(slope,2),
        "active_in_t3":    int((g["order_date"] >= "2026-03-01").any()),
    })

dealer_df = pd.DataFrame(dealer_stats)
dealer_df = dealer_df.merge(all_dealers, on="customer_code", how="left")

# Map dealer_df columns to match churn model's X_cols
# n_orders_q1_2025 / revenue_q1_2025 → use total stats as proxy
dealer_df["n_orders_q1_2025"] = dealer_df["n_orders_total"]
dealer_df["revenue_q1_2025"]  = dealer_df["revenue_total"]

# Dùng churn model để dự báo xác suất hoạt động
X_dealer = dealer_df[X_cols].fillna(0).values
dealer_df["prob_active_30d"] = (1 - pipe.predict_proba(X_dealer)[:,1]).round(4)
dealer_df["activity_risk"]   = pd.cut(dealer_df["prob_active_30d"],
                                       bins=[0,.3,.6,1.0],
                                       labels=["Nguy cơ cao","Trung bình","Tích cực"],
                                       include_lowest=True)
dealer_df["priority_contact"] = (dealer_df["prob_active_30d"] < 0.3).astype(int)

dealer_df.to_csv(OUT_FCST / "c3_dealer_activity.csv", **QW)
log.info(f"  c3_dealer_activity.csv    {len(dealer_df):>4} rows")

# ════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════
log.info("─"*55)
log.info("✓ Xong! Tất cả CSV:")
for d in [OUT_DATA, OUT_DASH, OUT_FCST]:
    for fp in sorted(d.glob("*.csv")):
        rows = sum(1 for _ in open(fp, encoding="utf-8-sig")) - 1
        kb   = fp.stat().st_size // 1024
        log.info(f"  {str(fp.relative_to(fp.parent.parent.parent)):<45} {rows:>6,} rows  {kb:>4}KB")
