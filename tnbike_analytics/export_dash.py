"""
export_dash.py
Xuất 5 CSV toàn diện để vẽ dashboard — không fit trên toàn bộ data.

Data: Q1-2025 (2025-01..03) + Q1-2026 (2026-01..02) — 5 tháng, 17k dòng

Output (output/dash/):
  01_monthly_series.csv    — time series tháng × nhóm SP × vùng, mọi aggregation
  02_geo_product.csv       — tỉnh × nhóm SP, rollup vùng + quốc gia
  03_sku_catalog.csv       — mã SP với BCG, Pareto, YoY, phân tích màu
  04_customer_analytics.csv — RFM + Churn ML (temporal split: Q1-2025→Q1-2026)
  05_forecast.csv          — Prophet forecast (train→Jan-2026, test→Feb-2026,
                             forecast→Mar-Jun 2026) kèm confidence band

Train/Test split:
  Forecast : train 2025-01..2026-01 | test 2026-02 | forecast 2026-03..06
  Churn    : features từ Q1-2025 | label = có mua Q1-2026 không | 80/20 stratified
             Dùng Pipeline(StandardScaler + GBM) → zero data leakage
"""

import sys
import logging
import warnings
import numpy as np
import pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("export_dash")

sys.path.insert(0, str(Path(__file__).parent))
from analytics.sql_data_loader import load_all, build_fact

OUT = Path(__file__).parent / "output" / "dash"
OUT.mkdir(parents=True, exist_ok=True)

# ─── Load ────────────────────────────────────────────────────────────────────
log.info("Loading fact table...")
dfs  = load_all()
fact = build_fact(dfs)
fact["order_date"] = pd.to_datetime(fact["order_date"])
fact["ym"]         = fact["order_date"].dt.to_period("M").astype(str)

DATA_START = pd.Timestamp(fact["order_date"].min().date())
DATA_END   = pd.Timestamp(fact["order_date"].max().date())
log.info(f"  {len(fact):,} dòng  |  {DATA_START.date()} → {DATA_END.date()}")

GROUP_LABEL = {
    "CITYBIKE_P":  "Xe phổ thông",
    "KIDBIKE_1":   "Xe trẻ em N1",
    "KIDBIKE_2":   "Xe trẻ em N2",
    "SPORTBIKE_S": "Thể thao thép",
    "SPORTBIKE_A": "Thể thao nhôm",
}


# ─── Helper ──────────────────────────────────────────────────────────────────
def agg4(df, keys):
    """Aggregate revenue/qty/orders/customers theo keys."""
    return (
        df.groupby(keys, dropna=False)
        .agg(
            revenue     =("line_total",     "sum"),
            quantity    =("quantity",        "sum"),
            n_orders    =("so_number",       "nunique"),
            n_customers =("customer_code",  "nunique"),
        )
        .reset_index()
    )


def pct_change_group(df, group_cols, val_col, sort_cols):
    df = df.sort_values(group_cols + sort_cols)
    return df.groupby(group_cols)[val_col].pct_change().mul(100).round(2)


# ═════════════════════════════════════════════════════════════════════════════
# CSV 1 — monthly_series.csv
# Grain: (year, month) × group_code × region  +  rollup rows
# ═════════════════════════════════════════════════════════════════════════════
log.info("─" * 60)
log.info("CSV 1: monthly_series.csv")

BASE = ["fiscal_year", "fiscal_month", "ym"]

chunks = []
for extra, label in [
    (["group_code", "group_name", "region"],  "group_region"),
    (["group_code", "group_name"],            "group"),
    (["region"],                              "region"),
    ([],                                      "total"),
]:
    c = agg4(fact, BASE + extra)
    for col in ["group_code", "group_name", "region"]:
        if col not in c.columns:
            c[col] = "__ALL__"
    c["agg_level"] = label
    chunks.append(c)

ms = pd.concat(chunks, ignore_index=True)
ms["fiscal_year"]  = ms["fiscal_year"].astype(int)
ms["fiscal_month"] = ms["fiscal_month"].astype(int)
ms["period_label"] = ms.apply(lambda r: f"T{r.fiscal_month}/{r.fiscal_year}", axis=1)

# MoM growth (trong cùng group × region × agg_level)
ms = ms.sort_values(["agg_level", "group_code", "region", "fiscal_year", "fiscal_month"])
ms["mom_revenue_pct"] = pct_change_group(
    ms, ["agg_level", "group_code", "region"], "revenue",
    ["fiscal_year", "fiscal_month"]
)

# YoY (cùng tháng, năm trước — Q1-2025 vs Q1-2026)
base25 = (
    ms[ms.fiscal_year == 2025]
    [["fiscal_month", "agg_level", "group_code", "region", "revenue"]]
    .rename(columns={"revenue": "rev_2025"})
)
ms = ms.merge(base25, on=["fiscal_month", "agg_level", "group_code", "region"], how="left")
ms["yoy_revenue_pct"] = (
    (ms["revenue"] - ms["rev_2025"]) / ms["rev_2025"].replace(0, np.nan) * 100
).round(2)
ms.drop(columns=["rev_2025"], inplace=True)

# Revenue share % of national total per tháng
nat = (
    ms[ms.agg_level == "total"]
    [["fiscal_year", "fiscal_month", "revenue"]]
    .rename(columns={"revenue": "rev_national"})
)
ms = ms.merge(nat, on=["fiscal_year", "fiscal_month"], how="left")
ms["revenue_share_pct"] = (ms["revenue"] / ms["rev_national"] * 100).round(2)
ms.drop(columns=["rev_national"], inplace=True)

# Cumulative YTD
ms = ms.sort_values(["agg_level", "group_code", "region", "fiscal_year", "fiscal_month"])
ms["cum_revenue_ytd"] = ms.groupby(
    ["agg_level", "group_code", "region", "fiscal_year"]
)["revenue"].cumsum().round(0).astype("Int64")

ms["revenue"]  = ms["revenue"].round(0).astype("Int64")
ms["quantity"] = ms["quantity"].round(0).astype("Int64")

ms.to_csv(OUT / "01_monthly_series.csv", index=False, encoding="utf-8-sig")
log.info(f"  → {len(ms):,} rows × {len(ms.columns)} cols")


# ═════════════════════════════════════════════════════════════════════════════
# CSV 2 — geo_product.csv
# Grain: province × group_code  +  rollup vùng, quốc gia
# ═════════════════════════════════════════════════════════════════════════════
log.info("─" * 60)
log.info("CSV 2: geo_product.csv")

geo_chunks = []

# province × group
pg = agg4(fact, ["province_name", "region", "group_code", "group_name"])
pg["agg_level"] = "province_group"
geo_chunks.append(pg)

# province total
pt = agg4(fact, ["province_name", "region"])
pt["group_code"] = "__ALL__"; pt["group_name"] = "Tất cả nhóm"
pt["agg_level"]  = "province"
geo_chunks.append(pt)

# region × group
rg = agg4(fact, ["region", "group_code", "group_name"])
rg["province_name"] = "__REGION__"; rg["agg_level"] = "region_group"
geo_chunks.append(rg)

# region total
rt = agg4(fact, ["region"])
rt["province_name"] = "__REGION__"; rt["group_code"] = "__ALL__"
rt["group_name"] = "Tất cả nhóm"; rt["agg_level"] = "region"
geo_chunks.append(rt)

# national × group
ng = agg4(fact, ["group_code", "group_name"])
ng["province_name"] = "__NATIONAL__"; ng["region"] = "__ALL__"
ng["agg_level"] = "national_group"
geo_chunks.append(ng)

# national total
nt_row = pd.DataFrame([{
    "province_name": "__NATIONAL__", "region": "__ALL__",
    "group_code": "__ALL__", "group_name": "Tất cả nhóm",
    "revenue": int(fact["line_total"].sum()),
    "quantity": int(fact["quantity"].sum()),
    "n_orders": fact["so_number"].nunique(),
    "n_customers": fact["customer_code"].nunique(),
    "agg_level": "national",
}])
geo_chunks.append(nt_row)

geo = pd.concat(geo_chunks, ignore_index=True)

# Lookup totals for %
prov_total = pt[["province_name", "revenue"]].rename(columns={"revenue": "_rev_prov"})
reg_total  = rt[["region", "revenue"]].rename(columns={"revenue": "_rev_reg"})
national_rev = int(fact["line_total"].sum())

geo = geo.merge(prov_total, on="province_name", how="left")
geo = geo.merge(reg_total,  on="region",        how="left")

geo["revenue_pct_province"] = (geo["revenue"] / geo["_rev_prov"] * 100).round(2)
geo["revenue_pct_region"]   = (geo["revenue"] / geo["_rev_reg"]  * 100).round(2)
geo["revenue_pct_national"] = (geo["revenue"] / national_rev     * 100).round(2)
geo.drop(columns=["_rev_prov", "_rev_reg"], inplace=True)

# Rank tỉnh trong vùng (theo doanh thu)
_prov_only = geo[geo.agg_level == "province"].copy()
_prov_only["rank_in_region"] = (
    _prov_only.groupby("region")["revenue"]
    .rank(ascending=False, method="dense").astype("Int64")
)
geo = geo.merge(
    _prov_only[["province_name", "region", "rank_in_region"]],
    on=["province_name", "region"], how="left"
)

geo["revenue"]  = geo["revenue"].round(0).astype("Int64")
geo["quantity"] = geo["quantity"].round(0).astype("Int64")

geo.to_csv(OUT / "02_geo_product.csv", index=False, encoding="utf-8-sig")
log.info(f"  → {len(geo):,} rows × {len(geo.columns)} cols")


# ═════════════════════════════════════════════════════════════════════════════
# CSV 3 — sku_catalog.csv
# Grain: product_code  — metrics tổng + theo năm + BCG + Pareto
# ═════════════════════════════════════════════════════════════════════════════
log.info("─" * 60)
log.info("CSV 3: sku_catalog.csv")

sku = agg4(fact, ["product_code", "product_name", "group_code", "group_name",
                  "line_name", "color"])
sku = sku.rename(columns={
    "revenue":     "revenue_total",
    "quantity":    "quantity_total",
    "n_orders":    "n_orders_total",
    "n_customers": "n_customers_total",
})

# Per-year metrics (2025: 3 tháng, 2026: 2 tháng)
for yr in [2025, 2026]:
    sub = fact[fact.fiscal_year == yr]
    yr_agg = (
        sub.groupby("product_code")
        .agg(**{
            f"revenue_{yr}":  ("line_total", "sum"),
            f"quantity_{yr}": ("quantity",   "sum"),
            f"n_orders_{yr}": ("so_number",  "nunique"),
        })
        .reset_index()
    )
    sku = sku.merge(yr_agg, on="product_code", how="left")

for col in [c for c in sku.columns if c.startswith(("revenue_", "quantity_", "n_orders_"))]:
    sku[col] = sku[col].fillna(0)

# Annualize 2026 (có 2 tháng → nhân 6 cho tương đương 12 tháng)
sku["revenue_2026_ann"] = sku["revenue_2026"] * 6

# YoY growth (annualized 2026 vs 2025)
sku["yoy_revenue_pct"] = (
    (sku["revenue_2026_ann"] - sku["revenue_2025"])
    / sku["revenue_2025"].replace(0, np.nan) * 100
).round(2)

# Avg unit price
sku["avg_unit_price"] = (
    sku["revenue_total"] / sku["quantity_total"].replace(0, np.nan)
).round(0).fillna(0).astype(int)

# Pareto (quốc gia)
sku = sku.sort_values("revenue_total", ascending=False).reset_index(drop=True)
sku["revenue_rank"]   = range(1, len(sku) + 1)
sku["pareto_cum_pct"] = (
    sku["revenue_total"].cumsum() / sku["revenue_total"].sum() * 100
).round(2)
sku["pareto_class"] = pd.cut(
    sku["pareto_cum_pct"], bins=[0, 70, 90, 100],
    labels=["A (top 70%)", "B (70-90%)", "C (90-100%)"]
)

# Revenue share trong nhóm SP
grp_rev = sku.groupby("group_code")["revenue_total"].sum().rename("_rev_group")
sku = sku.merge(grp_rev, on="group_code", how="left")
sku["revenue_share_in_group_pct"] = (
    sku["revenue_total"] / sku["_rev_group"] * 100
).round(2)
sku.drop(columns=["_rev_group"], inplace=True)

# BCG quadrant (trong từng nhóm SP: x=share, y=YoY growth)
bcg_parts = []
for gcode, grp in sku.groupby("group_code"):
    grp = grp.copy()
    med_share  = grp["revenue_share_in_group_pct"].median()
    valid_yoy  = grp["yoy_revenue_pct"].dropna()
    med_growth = valid_yoy.median() if len(valid_yoy) > 0 else 0.0

    def _bcg(row):
        hi_share  = row["revenue_share_in_group_pct"] >= med_share
        g = row["yoy_revenue_pct"]
        hi_growth = (g >= med_growth) if pd.notna(g) else False
        if hi_share and hi_growth:  return "Ngôi sao"
        if hi_share:                return "Bò sữa"
        if hi_growth:               return "Dấu hỏi"
        return "Con chó"

    grp["bcg_quadrant"] = grp.apply(_bcg, axis=1)
    bcg_parts.append(grp)

sku = pd.concat(bcg_parts, ignore_index=True)

for col in ["revenue_total", "revenue_2025", "revenue_2026", "revenue_2026_ann"]:
    sku[col] = sku[col].astype(int)
for col in ["quantity_total", "quantity_2025", "quantity_2026"]:
    sku[col] = sku[col].astype(int)

sku.to_csv(OUT / "03_sku_catalog.csv", index=False, encoding="utf-8-sig")
log.info(f"  → {len(sku):,} rows × {len(sku.columns)} cols")


# ═════════════════════════════════════════════════════════════════════════════
# CSV 4 — customer_analytics.csv
# Grain: customer_code
# Features: Q1-2025 | Label: có mua Q1-2026 không (0=active, 1=churn)
# ML: Pipeline(StandardScaler + GBM), 80/20 StratifiedShuffleSplit
# ═════════════════════════════════════════════════════════════════════════════
log.info("─" * 60)
log.info("CSV 4: customer_analytics.csv")

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import StratifiedShuffleSplit, cross_val_score
from sklearn.metrics import roc_auc_score, classification_report

FEAT_END = pd.Timestamp("2025-03-31")

q1_2025 = fact[fact.order_date <= FEAT_END].copy()
q1_2026 = fact[fact.order_date >= "2026-01-01"].copy()

# Universe: mọi khách hàng có đơn trong Q1-2025
universe_codes = q1_2025["customer_code"].unique()
log.info(f"  Universe: {len(universe_codes)} khách hàng")

# Lookup meta từ fact (tránh subquery)
cust_meta = (
    fact[["customer_code", "customer_name", "province_name", "region"]]
    .drop_duplicates("customer_code")
    .set_index("customer_code")
)

feats = []
for cust_code, grp in q1_2025.groupby("customer_code"):
    grp = grp.sort_values("order_date")
    last_order = grp["order_date"].max()

    # Trend slope (revenue theo tháng trong Q1-2025)
    monthly_rev = (
        grp.groupby(grp["order_date"].dt.to_period("M"))["line_total"].sum()
    )
    slope = 0.0
    if len(monthly_rev) >= 2:
        x = np.arange(len(monthly_rev))
        slope = float(np.polyfit(x, monthly_rev.values, 1)[0])

    meta = cust_meta.loc[cust_code] if cust_code in cust_meta.index else {}

    feats.append({
        "customer_code":            cust_code,
        "customer_name":            meta.get("customer_name", ""),
        "province_name":            meta.get("province_name", ""),
        "region":                   meta.get("region", ""),
        "first_order_date":         grp["order_date"].min().date(),
        "last_order_date_q1_2025":  last_order.date(),
        "cohort_month":             grp["order_date"].min().strftime("%Y-%m"),
        "recency_days":             (FEAT_END - last_order).days,
        "n_orders_q1_2025":         grp["so_number"].nunique(),
        "revenue_q1_2025":          int(grp["line_total"].sum()),
        "quantity_q1_2025":         int(grp["quantity"].sum()),
        "avg_order_value_q1_2025":  round(
            grp.groupby("so_number")["line_total"].sum().mean(), 0),
        "n_product_groups_q1_2025": grp["group_code"].nunique(),
        "trend_slope":              round(slope, 2),
        # Chi tiết nhóm SP đã mua
        "groups_bought":            "|".join(sorted(grp["group_code"].dropna().unique())),
    })

feat_df = pd.DataFrame(feats)

# ── Label: churn = không mua trong Q1-2026 ──
active_2026 = set(q1_2026["customer_code"].unique())
feat_df["churn_label"] = (~feat_df["customer_code"].isin(active_2026)).astype(int)
churn_rate = feat_df["churn_label"].mean()
log.info(f"  Churn rate: {churn_rate:.1%}  (label=1 nếu không mua lại trong Q1-2026)")

# ── RFM Scoring (quintile) ──
for col, score_col, ascending in [
    ("recency_days",            "rfm_r", True),   # thấp hơn = tốt hơn
    ("n_orders_q1_2025",        "rfm_f", False),
    ("revenue_q1_2025",         "rfm_m", False),
]:
    ranks = feat_df[col].rank(pct=True, method="average")
    if ascending:  # recency: ít ngày = score cao
        feat_df[score_col] = pd.cut(
            ranks, bins=[0, .2, .4, .6, .8, 1.0],
            labels=[5, 4, 3, 2, 1], include_lowest=True
        ).astype(int)
    else:
        feat_df[score_col] = pd.cut(
            ranks, bins=[0, .2, .4, .6, .8, 1.0],
            labels=[1, 2, 3, 4, 5], include_lowest=True
        ).astype(int)

def rfm_segment(r, f, m):
    if r >= 4 and f >= 4 and m >= 4: return "Khách hàng tiêu biểu"
    if r >= 4 and f >= 3:             return "Khách hàng trung thành"
    if r >= 4:                        return "Khách hàng mới tiềm năng"
    if r <= 2 and f >= 4:             return "Cần chăm sóc đặc biệt"
    if r <= 2:                        return "Có nguy cơ rời bỏ"
    return "Cần theo dõi"

feat_df["rfm_segment"] = feat_df.apply(
    lambda row: rfm_segment(row.rfm_r, row.rfm_f, row.rfm_m), axis=1)

# ── Churn ML: train/test 80/20 stratified ──
X_cols = [
    "recency_days", "n_orders_q1_2025", "revenue_q1_2025",
    "avg_order_value_q1_2025", "n_product_groups_q1_2025", "trend_slope",
]
X = feat_df[X_cols].fillna(0).values
y = feat_df["churn_label"].values

sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(sss.split(X, y))

# Pipeline: scaler fit chỉ trong fold → không data leakage
pipe = Pipeline([
    ("scaler", StandardScaler()),
    ("clf",    GradientBoostingClassifier(n_estimators=200, learning_rate=0.05,
                                          max_depth=3, random_state=42)),
])

# Cross-validate trên train set
cv_scores = cross_val_score(pipe, X[train_idx], y[train_idx], cv=5, scoring="roc_auc")
log.info(f"  CV ROC-AUC (5-fold, train only): {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

# Fit trên train, evaluate trên held-out test
pipe.fit(X[train_idx], y[train_idx])
prob_test = pipe.predict_proba(X[test_idx])[:, 1]
roc_test  = roc_auc_score(y[test_idx], prob_test)
log.info(f"  ROC-AUC (held-out test): {roc_test:.3f}")
log.info(f"\n{classification_report(y[test_idx], (prob_test >= 0.5).astype(int), zero_division=0)}")

# Predictions cho toàn bộ universe (model chỉ train trên 80%)
feat_df["churn_prob"]  = pipe.predict_proba(X)[:, 1].round(4)
feat_df["churn_split"] = "train"
feat_df.loc[feat_df.index[test_idx], "churn_split"] = "test"
feat_df["churn_priority"] = pd.cut(
    feat_df["churn_prob"],
    bins=[0, 0.30, 0.60, 1.0],
    labels=["Thấp", "Trung bình", "Cao"],
    include_lowest=True,
)
feat_df["roc_auc_test"] = round(roc_test, 4)

# Merge Q1-2026 actuals (để dash so sánh dự báo vs thực tế)
q1_2026_agg = (
    q1_2026.groupby("customer_code")
    .agg(
        n_orders_q1_2026  = ("so_number",     "nunique"),
        revenue_q1_2026   = ("line_total",     "sum"),
        quantity_q1_2026  = ("quantity",       "sum"),
    )
    .reset_index()
)
feat_df = feat_df.merge(q1_2026_agg, on="customer_code", how="left")
for c in ["n_orders_q1_2026", "revenue_q1_2026", "quantity_q1_2026"]:
    feat_df[c] = feat_df[c].fillna(0)
feat_df["revenue_q1_2026"] = feat_df["revenue_q1_2026"].astype(int)
feat_df["revenue_q1_2025"] = feat_df["revenue_q1_2025"].astype(int)

feat_df.to_csv(OUT / "04_customer_analytics.csv", index=False, encoding="utf-8-sig")
log.info(f"  → {len(feat_df):,} rows × {len(feat_df.columns)} cols")


# ═════════════════════════════════════════════════════════════════════════════
# CSV 5 — forecast.csv
# Train: 2025-01-01 → 2026-01-31  |  Test: 2026-02  |  Forecast: 2026-03..06
# ═════════════════════════════════════════════════════════════════════════════
log.info("─" * 60)
log.info("CSV 5: forecast.csv")

try:
    from prophet import Prophet
    HAS_PROPHET = True
except ImportError:
    log.warning("  Prophet chưa được cài đặt — bỏ qua CSV 5")
    HAS_PROPHET = False

if HAS_PROPHET:
    TRAIN_END  = pd.Timestamp("2026-01-31")
    TEST_START = pd.Timestamp("2026-02-01")
    TEST_END   = DATA_END
    FCST_END   = pd.Timestamp("2026-06-30")

    all_fc = []

    for group_code in sorted(fact["group_code"].dropna().unique()):
        grp_name = GROUP_LABEL.get(group_code, group_code)

        # Daily revenue cho nhóm này
        daily = (
            fact[fact.group_code == group_code]
            .groupby("order_date")["line_total"].sum()
            .reset_index()
            .rename(columns={"order_date": "ds", "line_total": "y"})
        )
        daily["ds"] = pd.to_datetime(daily["ds"])

        train_ts = daily[daily.ds <= TRAIN_END].copy()
        if len(train_ts) < 10:
            log.warning(f"  Bỏ qua {group_code}: {len(train_ts)} ngày train")
            continue

        log.info(f"  Forecasting {grp_name} ({len(train_ts)} ngày train)...")

        cap   = float(train_ts["y"].max() * 2.5)
        train_ts["cap"]   = cap
        train_ts["floor"] = 0.0

        # Yearly seasonality tắt (chỉ có 3 tháng train + gap → không đủ)
        model = Prophet(
            growth                  = "logistic",
            yearly_seasonality      = False,
            weekly_seasonality      = True,
            daily_seasonality       = False,
            seasonality_mode        = "multiplicative",
            changepoint_prior_scale = 0.10,
        )
        model.add_country_holidays(country_name="VN")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(train_ts)

        n_days  = (FCST_END - train_ts["ds"].max()).days
        future  = model.make_future_dataframe(periods=n_days)
        future["cap"]   = cap
        future["floor"] = 0.0
        fc = model.predict(future)

        for col in ["yhat", "yhat_lower", "yhat_upper"]:
            fc[col] = fc[col].clip(lower=0).round(0).astype(int)

        fc = fc[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
        fc["ds"] = pd.to_datetime(fc["ds"])

        # Merge actuals
        fc = fc.merge(
            daily.rename(columns={"y": "y_actual"}), on="ds", how="left"
        )
        fc["y_actual"] = fc["y_actual"].fillna(0).astype(int)

        # Split labels
        fc["split"] = "train"
        fc.loc[(fc.ds >= TEST_START) & (fc.ds <= TEST_END), "split"] = "test"
        fc.loc[fc.ds > TEST_END, "split"] = "forecast"

        # Metrics trên test (Feb 2026)
        test_rows = fc[(fc.split == "test") & (fc.y_actual > 0)]
        if len(test_rows) > 0:
            mae  = float(np.abs(test_rows["yhat"] - test_rows["y_actual"]).mean())
            denom = test_rows["y_actual"].replace(0, np.nan)
            mape = float((np.abs(test_rows["yhat"] - test_rows["y_actual"]) / denom)
                         .mean() * 100)
        else:
            mae, mape = np.nan, np.nan

        log.info(f"    MAE={mae:,.0f}  MAPE={mape:.1f}%")

        fc["group_code"]     = group_code
        fc["group_name"]     = grp_name
        fc["month_label"]    = fc["ds"].dt.strftime("%Y-%m")
        fc["period_label"]   = fc["ds"].apply(lambda d: f"T{d.month}/{d.year}")
        fc["is_future"]      = (fc.ds > TEST_END).astype(int)
        fc["mae_test"]       = round(mae, 0) if not np.isnan(mae) else np.nan
        fc["mape_test_pct"]  = round(mape, 2) if not np.isnan(mape) else np.nan

        # Chỉ giữ ngày từ đầu data đến cuối forecast
        fc = fc[(fc.ds >= DATA_START) & (fc.ds <= FCST_END)].copy()
        all_fc.append(fc)

    if all_fc:
        forecast_df = pd.concat(all_fc, ignore_index=True)
        forecast_df.to_csv(OUT / "05_forecast.csv", index=False, encoding="utf-8-sig")
        log.info(f"  → {len(forecast_df):,} rows × {len(forecast_df.columns)} cols")
    else:
        log.warning("  Không có dữ liệu forecast nào được tạo")


# ─── Summary ─────────────────────────────────────────────────────────────────
log.info("─" * 60)
log.info("✓ Hoàn thành! Output:")
for f in sorted(OUT.glob("*.csv")):
    rows = sum(1 for _ in open(f, encoding="utf-8-sig")) - 1
    size_kb = f.stat().st_size // 1024
    log.info(f"  {f.name:<35}  {rows:>6,} rows  {size_kb:>5} KB")
