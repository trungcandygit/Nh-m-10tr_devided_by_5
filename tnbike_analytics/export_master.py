"""
export_master.py
Pipeline đầy đủ SQL → 2 CSV siêu toàn diện cho dashboard.

Source: sql/02_import_data.sql  (không cần DB, không cần CSV trung gian)

Output → output/master/
  fact_full.csv    17k rows × ~45 cols
                   Mỗi row = 1 order line + toàn bộ enrichment join vào:
                   RFM, churn_prob, BCG, Pareto, YoY, cohort...
                   → drill-down table, scatter, heatmap, lọc đa chiều

  agg_master.csv   ~2k rows × ~50 cols, cột grain phân loại aggregation
                   Grains: monthly_group_region | monthly_group | monthly_region |
                           monthly_total | province_group | province_total |
                           region_group | region_total | national_group |
                           national_total | sku | customer | forecast_daily
                   → mọi chart panel: line, bar, map, BCG bubble, churn table, forecast

Train / Test split:
  Churn   : features Q1-2025 | label = mua lại Q1-2026 | 80/20 stratified
            Pipeline(StandardScaler + GBM) — zero data leakage
  Forecast: train 2025-01→2026-01 | test 2026-02 | forecast 2026-03→06
"""

import csv
import sys, warnings, logging
import numpy as np
import pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("export_master")

sys.path.insert(0, str(Path(__file__).parent))
from analytics.sql_data_loader import load_all, build_fact

OUT = Path(__file__).parent / "output" / "master"
OUT.mkdir(parents=True, exist_ok=True)

GROUP_LABEL = {
    "CITYBIKE_P":  "Xe phổ thông",
    "KIDBIKE_1":   "Xe trẻ em N1",
    "KIDBIKE_2":   "Xe trẻ em N2",
    "SPORTBIKE_S": "Thể thao thép",
    "SPORTBIKE_A": "Thể thao nhôm",
}

# ════════════════════════════════════════════════════════════════
# 0. LOAD
# ════════════════════════════════════════════════════════════════
log.info("0. Loading fact table from SQL...")
dfs  = load_all()
fact = build_fact(dfs)
fact["order_date"]   = pd.to_datetime(fact["order_date"])
fact["ym"]           = fact["order_date"].dt.to_period("M").astype(str)
# Giữ product_code là string để tránh mất leading zeros khi đọc lại CSV
fact["product_code"] = fact["product_code"].astype(str)
# group_code NULL: sản phẩm không map được line_id trong nguồn SQL (72 SKU)
n_null_grp = fact["group_code"].isna().sum()
if n_null_grp:
    log.warning(f"   {n_null_grp} rows có group_code=NULL (72 SKU không có line_id trong SQL)")

DATA_START = fact["order_date"].min()
DATA_END   = fact["order_date"].max()
log.info(f"   {len(fact):,} rows | {DATA_START.date()} → {DATA_END.date()}")

FEAT_END  = pd.Timestamp("2025-03-31")   # cutoff features churn
TRAIN_END = pd.Timestamp("2026-01-31")   # cutoff train forecast


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════
def agg4(df, keys):
    return (df.groupby(keys, dropna=False)
              .agg(revenue=("line_total","sum"), quantity=("quantity","sum"),
                   n_orders=("so_number","nunique"), n_customers=("customer_code","nunique"))
              .reset_index())

def to_int(s):
    return s.round(0).astype("Int64")


# ════════════════════════════════════════════════════════════════
# 1. SKU ENRICHMENT TABLE  (join vào fact_full + agg_master)
# ════════════════════════════════════════════════════════════════
log.info("1. Computing SKU enrichment...")

sku = agg4(fact, ["product_code","product_name","group_code","group_name","line_name","color"])
sku.rename(columns={"revenue":"rev_sku","quantity":"qty_sku",
                     "n_orders":"ord_sku","n_customers":"cust_sku"}, inplace=True)

for yr in [2025, 2026]:
    sub = fact[fact.fiscal_year == yr].groupby("product_code").agg(
        **{f"rev_{yr}": ("line_total","sum"), f"qty_{yr}": ("quantity","sum"),
           f"ord_{yr}": ("so_number","nunique")}).reset_index()
    sku = sku.merge(sub, on="product_code", how="left")

for c in [x for x in sku.columns if x.startswith(("rev_","qty_","ord_")) and x != "rev_sku"]:
    sku[c] = sku[c].fillna(0)

sku["rev_2026_ann"]          = sku["rev_2026"] * 6
sku["yoy_rev_pct"]           = ((sku["rev_2026_ann"] - sku["rev_2025"])
                                 / sku["rev_2025"].replace(0, np.nan) * 100).round(2)
sku["avg_unit_price"]        = (sku["rev_sku"] / sku["qty_sku"].replace(0, np.nan)).round(0).fillna(0)
sku = sku.sort_values("rev_sku", ascending=False).reset_index(drop=True)
sku["revenue_rank"]          = range(1, len(sku)+1)
sku["pareto_cum_pct"]        = (sku["rev_sku"].cumsum() / sku["rev_sku"].sum() * 100).round(2)
sku["pareto_class"]          = pd.cut(sku["pareto_cum_pct"], bins=[0,70,90,100],
                                       labels=["A","B","C"])
grp_rev = sku.groupby("group_code")["rev_sku"].sum()
sku["rev_share_in_group_pct"] = (sku["rev_sku"] / sku["group_code"].map(grp_rev) * 100).round(2)

# BCG trong nhóm
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


# ════════════════════════════════════════════════════════════════
# 2. CUSTOMER ENRICHMENT  (RFM + Churn ML)
# ════════════════════════════════════════════════════════════════
log.info("2. Computing customer RFM + Churn ML...")

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import StratifiedShuffleSplit, cross_val_score
from sklearn.metrics import roc_auc_score, classification_report

q1_2025 = fact[fact.order_date <= FEAT_END]
q1_2026 = fact[fact.order_date >= "2026-01-01"]
active_2026 = set(q1_2026["customer_code"].unique())

cust_meta = (fact[["customer_code","customer_name","province_name","region"]]
             .drop_duplicates("customer_code").set_index("customer_code"))

feats = []
for cc, g in q1_2025.groupby("customer_code"):
    g = g.sort_values("order_date")
    last = g["order_date"].max()
    monthly_rev = g.groupby(g["order_date"].dt.to_period("M"))["line_total"].sum()
    slope = 0.0
    if len(monthly_rev) >= 2:
        x = np.arange(len(monthly_rev))
        slope = float(np.polyfit(x, monthly_rev.values, 1)[0])
    m = cust_meta.loc[cc] if cc in cust_meta.index else {}
    feats.append({
        "customer_code":      cc,
        "customer_name":      m.get("customer_name",""),
        "province_name":      m.get("province_name",""),
        "region":             m.get("region",""),
        "cohort_month":       g["order_date"].min().strftime("%Y-%m"),
        "first_order_date":   g["order_date"].min().date(),
        "last_order_q1_2025": last.date(),
        "recency_days":       (FEAT_END - last).days,
        "n_orders_q1_2025":   g["so_number"].nunique(),
        "revenue_q1_2025":    int(g["line_total"].sum()),
        "quantity_q1_2025":   int(g["quantity"].sum()),
        "avg_order_value":    round(g.groupby("so_number")["line_total"].sum().mean(), 0),
        "n_product_groups":   g["group_code"].nunique(),
        "trend_slope":        round(slope, 2),
        "groups_bought":      "|".join(sorted(g["group_code"].dropna().unique())),
    })

cdf = pd.DataFrame(feats)
cdf["churn_label"] = (~cdf["customer_code"].isin(active_2026)).astype(int)
log.info(f"   Universe: {len(cdf)} customers | churn rate: {cdf.churn_label.mean():.1%}")

# RFM quintile scoring
for col, sc, asc in [
    ("recency_days",     "rfm_r", True),
    ("n_orders_q1_2025", "rfm_f", False),
    ("revenue_q1_2025",  "rfm_m", False),
]:
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

# Churn ML: 80/20 stratified, Pipeline để tránh data leakage
X_cols = ["recency_days","n_orders_q1_2025","revenue_q1_2025",
          "avg_order_value","n_product_groups","trend_slope"]
X = cdf[X_cols].fillna(0).values
y = cdf["churn_label"].values

sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
tr_idx, te_idx = next(sss.split(X, y))

pipe = Pipeline([("sc", StandardScaler()),
                 ("cl", GradientBoostingClassifier(n_estimators=200, learning_rate=0.05,
                                                    max_depth=3, random_state=42))])
cv = cross_val_score(pipe, X[tr_idx], y[tr_idx], cv=5, scoring="roc_auc")
log.info(f"   CV ROC-AUC (train-only): {cv.mean():.3f} ± {cv.std():.3f}")

pipe.fit(X[tr_idx], y[tr_idx])
prob_te = pipe.predict_proba(X[te_idx])[:,1]
roc_te  = roc_auc_score(y[te_idx], prob_te)
log.info(f"   ROC-AUC (held-out test): {roc_te:.3f}")
log.info(f"\n{classification_report(y[te_idx],(prob_te>=.5).astype(int),zero_division=0)}")

cdf["churn_prob"]     = pipe.predict_proba(X)[:,1].round(4)
cdf["churn_split"]    = "train"
cdf.loc[cdf.index[te_idx], "churn_split"] = "test"
cdf["churn_priority"] = pd.cut(cdf["churn_prob"], bins=[0,.3,.6,1.0],
                                labels=["Thấp","Trung bình","Cao"], include_lowest=True)
cdf["roc_auc_test"]   = round(roc_te, 4)

q26 = q1_2026.groupby("customer_code").agg(
    n_orders_q1_2026=("so_number","nunique"),
    revenue_q1_2026 =("line_total","sum"),
).reset_index()
cdf = cdf.merge(q26, on="customer_code", how="left")
cdf["n_orders_q1_2026"] = cdf["n_orders_q1_2026"].fillna(0).astype(int)
cdf["revenue_q1_2026"]  = cdf["revenue_q1_2026"].fillna(0).astype(int)


# ════════════════════════════════════════════════════════════════
# 3. FORECAST  (Prophet, temporal split)
# ════════════════════════════════════════════════════════════════
log.info("3. Running Prophet forecast...")

forecast_rows = []
try:
    from prophet import Prophet
    TEST_START = pd.Timestamp("2026-02-01")
    FCST_END   = pd.Timestamp("2026-06-30")

    for gc in sorted(fact["group_code"].dropna().unique()):
        daily = (fact[fact.group_code == gc]
                 .groupby("order_date")["line_total"].sum()
                 .reset_index().rename(columns={"order_date":"ds","line_total":"y"}))
        daily["ds"] = pd.to_datetime(daily["ds"])
        train_ts = daily[daily.ds <= TRAIN_END].copy()
        if len(train_ts) < 10:
            continue
        cap = float(train_ts["y"].max() * 2.5)
        train_ts["cap"] = cap; train_ts["floor"] = 0.0

        m = Prophet(growth="logistic", yearly_seasonality=False,
                    weekly_seasonality=True, daily_seasonality=False,
                    seasonality_mode="multiplicative", changepoint_prior_scale=0.10)
        m.add_country_holidays(country_name="VN")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m.fit(train_ts)

        n_days = (FCST_END - train_ts["ds"].max()).days
        fut = m.make_future_dataframe(periods=n_days)
        fut["cap"] = cap; fut["floor"] = 0.0
        fc = m.predict(fut)
        for col in ["yhat","yhat_lower","yhat_upper"]:
            fc[col] = fc[col].clip(lower=0)

        fc = fc[["ds","yhat","yhat_lower","yhat_upper"]].merge(
            daily.rename(columns={"y":"y_actual"}), on="ds", how="left")
        fc["y_actual"] = fc["y_actual"].fillna(0).astype(int)
        fc["split"] = "train"
        fc.loc[(fc.ds >= TEST_START) & (fc.ds <= DATA_END), "split"] = "test"
        fc.loc[fc.ds > DATA_END, "split"] = "forecast"

        test_r = fc[(fc.split == "test") & (fc.y_actual > 0)]
        mae  = float(np.abs(test_r.yhat - test_r.y_actual).mean()) if len(test_r) else np.nan
        denom = test_r.y_actual.replace(0, np.nan)
        mape = float((np.abs(test_r.yhat - test_r.y_actual)/denom).mean()*100) if len(test_r) else np.nan
        log.info(f"   {GROUP_LABEL.get(gc,gc)}: MAE={mae:,.0f}  MAPE={mape:.1f}%")

        fc["group_code"] = gc
        fc["group_name"] = GROUP_LABEL.get(gc, gc)
        fc["is_future"]  = (fc.ds > DATA_END).astype(int)
        fc["mae_test"]   = round(mae, 0) if not np.isnan(mae) else np.nan
        fc["mape_test_pct"] = round(mape, 2) if not np.isnan(mape) else np.nan
        fc = fc[(fc.ds >= DATA_START) & (fc.ds <= FCST_END)]
        forecast_rows.append(fc)
except ImportError:
    log.warning("   Prophet chưa cài — bỏ qua forecast")

fcst_df = pd.concat(forecast_rows, ignore_index=True) if forecast_rows else pd.DataFrame()


# ════════════════════════════════════════════════════════════════
# 4. FACT_FULL.CSV
#    17k rows × ~45 cols: mọi enrichment join về từng order line
# ════════════════════════════════════════════════════════════════
log.info("4. Building fact_full.csv...")

f = fact.copy()

# Time enrichment
f["period_label"]  = f.apply(lambda r: f"T{r.fiscal_month}/{r.fiscal_year}", axis=1)
f["quarter_label"] = f.apply(lambda r: f"Q{r.fiscal_quarter}/{r.fiscal_year}", axis=1)
f["day_of_week"]   = f["order_date"].dt.dayofweek          # 0=Mon
f["week_of_year"]  = f["order_date"].dt.isocalendar().week.astype(int)
f["is_weekend"]    = (f["day_of_week"] >= 5).astype(int)

# Order context (sum all lines in same SO)
ord_total = (f.groupby("so_number")["line_total"].sum().rename("order_total")
              .reset_index())
ord_lines = (f.groupby("so_number")["product_code"].count().rename("n_lines_in_order")
              .reset_index())
f = f.merge(ord_total, on="so_number", how="left")
f = f.merge(ord_lines, on="so_number", how="left")
f["line_share_of_order_pct"] = (f["line_total"] / f["order_total"] * 100).round(2)

# SKU enrichment
sku_join = sku[["product_code","revenue_rank","pareto_class","bcg_quadrant",
                "rev_share_in_group_pct","yoy_rev_pct","avg_unit_price",
                "pareto_cum_pct"]].copy()
sku_join.columns = ["product_code","sku_revenue_rank","sku_pareto_class",
                    "sku_bcg_quadrant","sku_rev_share_group_pct",
                    "sku_yoy_rev_pct","sku_avg_unit_price","sku_pareto_cum_pct"]
f = f.merge(sku_join, on="product_code", how="left")

# Customer enrichment
cust_join = cdf[["customer_code","cohort_month","recency_days",
                 "n_orders_q1_2025","revenue_q1_2025","avg_order_value",
                 "rfm_r","rfm_f","rfm_m","rfm_segment",
                 "churn_label","churn_prob","churn_priority"]].copy()
cust_join.columns = (["customer_code","cust_cohort_month","cust_recency_days",
                      "cust_n_orders_q1_2025","cust_revenue_q1_2025","cust_avg_order_value",
                      "cust_rfm_r","cust_rfm_f","cust_rfm_m","cust_rfm_segment",
                      "cust_churn_label","cust_churn_prob","cust_churn_priority"])
f = f.merge(cust_join, on="customer_code", how="left")

f["line_total"]   = f["line_total"].astype(int)
f["order_total"]  = f["order_total"].astype(int)
f["unit_price"]   = f["unit_price"].round(2)

f.to_csv(OUT / "fact_full.csv", index=False, encoding="utf-8-sig",
         quoting=csv.QUOTE_NONNUMERIC)
log.info(f"   → {len(f):,} rows × {len(f.columns)} cols")


# ════════════════════════════════════════════════════════════════
# 5. AGG_MASTER.CSV
#    ~2k rows × ~50 cols, cột grain phân loại
# ════════════════════════════════════════════════════════════════
log.info("5. Building agg_master.csv...")

BASE_TIME = ["fiscal_year","fiscal_month","fiscal_quarter","ym"]
all_grains = []

# ── helper: thêm period_label sau khi agg ──
def add_period(df):
    if "fiscal_month" in df.columns and "fiscal_year" in df.columns:
        df["period_label"] = df.apply(
            lambda r: f"T{int(r.fiscal_month)}/{int(r.fiscal_year)}", axis=1)
    return df

# ── helper: MoM / YoY / YTD cho time-series ──
def add_time_metrics(df, group_by_cols):
    df = df.sort_values(group_by_cols + ["fiscal_year","fiscal_month"])
    df["mom_revenue_pct"] = (
        df.groupby(group_by_cols)["revenue"].pct_change() * 100).round(2)
    base25 = df[df.fiscal_year==2025][
        ["fiscal_month"] + group_by_cols + ["revenue"]
    ].rename(columns={"revenue":"_r25"})
    df = df.merge(base25, on=["fiscal_month"]+group_by_cols, how="left")
    df["yoy_revenue_pct"] = (
        (df["revenue"]-df["_r25"]) / df["_r25"].replace(0,np.nan) * 100).round(2)
    df.drop(columns=["_r25"], inplace=True)
    nat_m = df[df.get("agg_level","") == "monthly_total"] if "agg_level" in df.columns else df
    return df

# ─── 5a. Monthly time-series ──────────────────────────────────
for extra, label in [
    (["group_code","group_name","region"],  "monthly_group_region"),
    (["group_code","group_name"],           "monthly_group"),
    (["region"],                            "monthly_region"),
    ([],                                    "monthly_total"),
]:
    c = agg4(fact, BASE_TIME + extra)
    for col in ["group_code","group_name","region"]:
        if col not in c.columns: c[col] = "__ALL__"
    c["grain"] = label
    add_period(c)
    all_grains.append(c)

# MoM / YoY trên bản gộp tất cả monthly rows
monthly_df = pd.concat(
    [g for g in all_grains if g["grain"].iloc[0].startswith("monthly")],
    ignore_index=True)
monthly_df = monthly_df.sort_values(["grain","group_code","region","fiscal_year","fiscal_month"])
monthly_df["mom_revenue_pct"] = (
    monthly_df.groupby(["grain","group_code","region"])["revenue"]
    .pct_change().mul(100).round(2))
base25 = monthly_df[monthly_df.fiscal_year==2025][
    ["fiscal_month","grain","group_code","region","revenue"]
].rename(columns={"revenue":"_r25"})
monthly_df = monthly_df.merge(base25, on=["fiscal_month","grain","group_code","region"], how="left")
monthly_df["yoy_revenue_pct"] = (
    (monthly_df["revenue"]-monthly_df["_r25"])
    / monthly_df["_r25"].replace(0,np.nan) * 100).round(2)
monthly_df.drop(columns=["_r25"], inplace=True)
# Năm gốc (2025) không có năm trước để so → NaN, không phải 0
monthly_df.loc[monthly_df["fiscal_year"] == 2025, "yoy_revenue_pct"] = np.nan

# National total per month (cho revenue_share_pct)
nat_m = monthly_df[monthly_df.grain=="monthly_total"][
    ["fiscal_year","fiscal_month","revenue"]].rename(columns={"revenue":"_rev_nat"})
monthly_df = monthly_df.merge(nat_m, on=["fiscal_year","fiscal_month"], how="left")
monthly_df["revenue_share_pct"] = (
    monthly_df["revenue"] / monthly_df["_rev_nat"] * 100).round(2)
monthly_df.drop(columns=["_rev_nat"], inplace=True)

monthly_df = monthly_df.sort_values(["grain","group_code","region","fiscal_year","fiscal_month"])
monthly_df["cum_revenue_ytd"] = monthly_df.groupby(
    ["grain","group_code","region","fiscal_year"])["revenue"].cumsum()

# Thay các grains monthly trong all_grains bằng bản đã enriched
all_grains = [g for g in all_grains if not g["grain"].iloc[0].startswith("monthly")]
all_grains.append(monthly_df)

# ─── 5b. Geographic ───────────────────────────────────────────
for keys, label, fill in [
    (["province_name","region","group_code","group_name"], "province_group",   {}),
    (["province_name","region"],                           "province_total",   {"group_code":"__ALL__","group_name":"Tất cả nhóm"}),
    (["region","group_code","group_name"],                 "region_group",     {"province_name":"__REGION__"}),
    (["region"],                                           "region_total",     {"province_name":"__REGION__","group_code":"__ALL__","group_name":"Tất cả nhóm"}),
    (["group_code","group_name"],                          "national_group",   {"province_name":"__NATIONAL__","region":"__ALL__"}),
]:
    c = agg4(fact, keys)
    for k,v in fill.items(): c[k] = v
    c["grain"] = label
    all_grains.append(c)

# National total
all_grains.append(pd.DataFrame([{
    "province_name":"__NATIONAL__","region":"__ALL__",
    "group_code":"__ALL__","group_name":"Tất cả nhóm",
    "revenue":int(fact["line_total"].sum()), "quantity":int(fact["quantity"].sum()),
    "n_orders":fact["so_number"].nunique(),"n_customers":fact["customer_code"].nunique(),
    "grain":"national_total",
}]))

# % metrics cho geo
_prov_rev = agg4(fact,["province_name","region"])[["province_name","revenue"]].rename(columns={"revenue":"_rp"})
_reg_rev  = agg4(fact,["region"])[["region","revenue"]].rename(columns={"revenue":"_rr"})
_nat_rev  = int(fact["line_total"].sum())

geo_grains = [g for g in all_grains if g["grain"].iloc[0] in
              ("province_group","province_total","region_group","region_total",
               "national_group","national_total")]
geo_df = pd.concat(geo_grains, ignore_index=True)
geo_df = geo_df.merge(_prov_rev, on="province_name", how="left")
geo_df = geo_df.merge(_reg_rev,  on="region",        how="left")
geo_df["revenue_pct_province"] = (geo_df["revenue"] / geo_df["_rp"] * 100).round(2)
geo_df["revenue_pct_region"]   = (geo_df["revenue"] / geo_df["_rr"] * 100).round(2)
geo_df["revenue_pct_national"] = (geo_df["revenue"] / _nat_rev * 100).round(2)
geo_df.drop(columns=["_rp","_rr"], inplace=True)

# Rank tỉnh trong vùng
_prov_only = geo_df[geo_df.grain=="province_total"].copy()
_prov_only["rank_in_region"] = (
    _prov_only.groupby("region")["revenue"].rank(ascending=False, method="dense").astype("Int64"))
geo_df = geo_df.merge(
    _prov_only[["province_name","region","rank_in_region"]],
    on=["province_name","region"], how="left")

all_grains = [g for g in all_grains if g["grain"].iloc[0] not in
              ("province_group","province_total","region_group","region_total",
               "national_group","national_total")]
all_grains.append(geo_df)

# ─── 5c. SKU grain ────────────────────────────────────────────
sku_grain = sku.rename(columns={
    "rev_sku":"revenue","qty_sku":"quantity","ord_sku":"n_orders","cust_sku":"n_customers",
    "rev_2025":"revenue_2025","qty_2025":"quantity_2025","ord_2025":"n_orders_2025",
    "rev_2026":"revenue_2026","qty_2026":"quantity_2026","ord_2026":"n_orders_2026",
    "rev_2026_ann":"revenue_2026_ann","yoy_rev_pct":"yoy_revenue_pct_ann",
    "rev_share_in_group_pct":"revenue_share_in_group_pct",
}).copy()
sku_grain["grain"] = "sku"
all_grains.append(sku_grain)

# ─── 5d. Customer grain ───────────────────────────────────────
cust_grain = cdf.copy()
cust_grain.rename(columns={
    "n_orders_q1_2025":"n_orders","revenue_q1_2025":"revenue",
    "quantity_q1_2025":"quantity",
}, inplace=True)
cust_grain["grain"] = "customer"
all_grains.append(cust_grain)

# ─── 5e. Forecast grain ───────────────────────────────────────
if not fcst_df.empty:
    fcst_df["grain"] = "forecast_daily"
    fcst_df["period_label"] = fcst_df["ds"].apply(lambda d: f"T{d.month}/{d.year}")
    fcst_df["ym"] = fcst_df["ds"].dt.strftime("%Y-%m")
    fcst_df["fiscal_year"]  = fcst_df["ds"].dt.year
    fcst_df["fiscal_month"] = fcst_df["ds"].dt.month
    all_grains.append(fcst_df)

# ─── 5f. Concat tất cả grains → 1 file ────────────────────────
agg_master = pd.concat(all_grains, ignore_index=True)

# Tidy numeric cols
for c in ["revenue","quantity","n_orders","n_customers",
          "revenue_2025","revenue_2026","revenue_2026_ann"]:
    if c in agg_master.columns:
        agg_master[c] = pd.to_numeric(agg_master[c], errors="coerce")
        agg_master[c] = agg_master[c].round(0).astype("Int64")

# grain ở đầu cho dễ đọc
cols = ["grain"] + [c for c in agg_master.columns if c != "grain"]
agg_master = agg_master[cols]

agg_master.to_csv(OUT / "agg_master.csv", index=False, encoding="utf-8-sig",
                  quoting=csv.QUOTE_NONNUMERIC)
log.info(f"   → {len(agg_master):,} rows × {len(agg_master.columns)} cols")


# ════════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════════
log.info("─" * 60)
log.info("✓ Xong! output/master/")
for fp in sorted(OUT.glob("*.csv")):
    rows = sum(1 for _ in open(fp, encoding="utf-8-sig")) - 1
    kb   = fp.stat().st_size // 1024
    log.info(f"  {fp.name:<22}  {rows:>6,} rows  {kb:>5} KB  ×{len(pd.read_csv(fp,nrows=0).columns)} cols")
