"""
prediction_engine.py — Tích hợp AI/ML từ 10 repo tham khảo

Câu hỏi 1 (Q1): Prophet group-level + weekly + top-20 SKU (từ elena-roff/time-series-prophet)
Câu hỏi 2 (Q2): K-Means slow-mover + seasonal color trend (từ beckyydo/retail-machine-learning)
Câu hỏi 3 (Q3): BG-NBD 30-day prob (từ mukulsinghal001/clv) +
                 LightGBM churn + SHAP (từ jamiubadmusng/customer-churn-prediction)
"""

import warnings, logging
import numpy as np
import pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")
log = logging.getLogger("tnbike.prediction")


# ═══════════════════════════════════════════════════════════════════
# CÂU HỎI 1 — Dự báo doanh số Q2/2026
# ═══════════════════════════════════════════════════════════════════

def run_q1_forecast(fact: pd.DataFrame) -> dict:
    """
    Prophet per nhóm sản phẩm → tổng hợp weekly + top-20 SKU.
    Kỹ thuật từ: elena-roff/time-series-prophet, AmirhosseinHonardoust/Market-IQ
    Returns: {
        'monthly':  DataFrame — tháng × nhóm SP (T1-2025 → T6-2026),
        'weekly':   DataFrame — tuần × nhóm SP (Q2/2026 only),
        'sku_q2':   DataFrame — SKU × tháng Q2 + top20 flag,
    }
    """
    from prophet import Prophet

    TRAIN_END = pd.Timestamp("2026-03-31")
    FCST_END  = pd.Timestamp("2026-06-30")

    fact = fact.copy()
    fact["order_date"] = pd.to_datetime(fact["order_date"])

    valid_groups = {"CITYBIKE_P", "KIDBIKE_1", "KIDBIKE_2", "SPORTBIKE_A", "SPORTBIKE_S"}
    all_rows = []
    for gc in sorted(g for g in fact["group_code"].dropna().unique() if g in valid_groups):
        daily = (fact[fact.group_code == gc]
                 .groupby("order_date")["line_total"].sum()
                 .reset_index().rename(columns={"order_date": "ds", "line_total": "y"}))
        daily["ds"] = pd.to_datetime(daily["ds"])
        train = daily[daily.ds <= TRAIN_END].copy()
        if len(train) < 10:
            continue
        cap = float(train["y"].max() * 2.5)
        train["cap"] = cap
        train["floor"] = 0.0

        m = Prophet(
            growth="logistic", weekly_seasonality=True,
            daily_seasonality=False, yearly_seasonality=False,
            seasonality_mode="multiplicative",
            changepoint_prior_scale=0.10,
        )
        m.add_country_holidays(country_name="VN")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m.fit(train)

        n_days = (FCST_END - train["ds"].max()).days
        fut = m.make_future_dataframe(periods=n_days)
        fut["cap"] = cap
        fut["floor"] = 0.0
        fc = m.predict(fut)
        for col in ["yhat", "yhat_lower", "yhat_upper"]:
            fc[col] = fc[col].clip(lower=0)

        fc = fc[["ds", "yhat", "yhat_lower", "yhat_upper"]].merge(
            daily.rename(columns={"y": "y_actual"}), on="ds", how="left")
        fc["y_actual"]    = fc["y_actual"].fillna(0).astype(int)
        fc["split"]       = "train"
        fc.loc[fc.ds > TRAIN_END, "split"] = "forecast"
        fc["group_code"]   = gc
        fc["fiscal_month"] = fc["ds"].dt.month
        fc["fiscal_year"]  = fc["ds"].dt.year
        fc = fc[fc.ds > pd.Timestamp("2025-01-01")]
        all_rows.append(fc)

    log.info(f"  Prophet: {len(all_rows)} nhóm SP")
    fcst = pd.concat(all_rows, ignore_index=True)

    # ── monthly summary ───────────────────────────────
    monthly = (fcst.groupby(["fiscal_year", "fiscal_month", "group_code", "split"])
               .agg(yhat=("yhat","sum"), yhat_lower=("yhat_lower","sum"),
                    yhat_upper=("yhat_upper","sum"), y_actual=("y_actual","sum"))
               .reset_index())
    monthly["ym"] = monthly.apply(
        lambda r: f"{int(r.fiscal_year)}-{int(r.fiscal_month):02d}", axis=1)

    # ── weekly (Q2 only — từ daily) ───────────────────
    fcst_dt = fcst.copy()
    fcst_dt["ds"] = pd.to_datetime(fcst_dt["ds"])
    q2_mask = (fcst_dt["fiscal_year"] == 2026) & fcst_dt["fiscal_month"].isin([4, 5, 6])
    weekly = (fcst_dt[q2_mask]
              .assign(yw=lambda d: d["ds"].dt.strftime("%G-W%V"),
                      week_start=lambda d: d["ds"].dt.to_period("W").apply(lambda p: str(p.start_time)[:10]))
              .groupby(["yw", "week_start", "group_code", "split"])
              .agg(yhat=("yhat","sum"), yhat_lower=("yhat_lower","sum"),
                   yhat_upper=("yhat_upper","sum"))
              .reset_index())

    # ── top-20 SKU Q2 — phân bổ từ group yhat xuống SKU ─
    sku_share = (fact[fact.fiscal_year == 2026]
                 .groupby(["group_code", "product_code", "product_name", "color", "line_name"])
                 ["line_total"].sum().reset_index(name="rev_q1_2026"))
    grp_tot = sku_share.groupby("group_code")["rev_q1_2026"].sum().rename("grp_total")
    sku_share = sku_share.merge(grp_tot, on="group_code", how="left")
    sku_share["sku_share"] = (sku_share["rev_q1_2026"] /
                               sku_share["grp_total"].replace(0, np.nan)).fillna(0)

    fcst_q2 = monthly[(monthly.fiscal_year == 2026) & monthly.fiscal_month.isin([4, 5, 6])].copy()
    sku_q2 = sku_share.merge(
        fcst_q2[["group_code", "fiscal_month", "yhat", "yhat_lower", "yhat_upper"]],
        on="group_code", how="inner")
    sku_q2["predicted_revenue"]       = (sku_q2["sku_share"] * sku_q2["yhat"]).round(0)
    sku_q2["predicted_revenue_lower"] = (sku_q2["sku_share"] * sku_q2["yhat_lower"]).round(0)
    sku_q2["predicted_revenue_upper"] = (sku_q2["sku_share"] * sku_q2["yhat_upper"]).round(0)
    sku_q2["ym"] = sku_q2["fiscal_month"].apply(lambda m: f"2026-{int(m):02d}")

    # Rank top-20 theo tổng Q2
    sku_q2_total = (sku_q2.groupby(["product_code", "product_name", "color", "line_name", "group_code"])
                    ["predicted_revenue"].sum().reset_index()
                    .sort_values("predicted_revenue", ascending=False).reset_index(drop=True))
    sku_q2_total["q2_rank"]    = sku_q2_total.index + 1
    sku_q2_total["top20_flag"] = (sku_q2_total["q2_rank"] <= 20).astype(int)
    sku_q2 = sku_q2.merge(
        sku_q2_total[["product_code", "q2_rank", "top20_flag"]], on="product_code", how="left")
    sku_q2 = sku_q2.drop(columns=["yhat", "yhat_lower", "yhat_upper", "grp_total", "sku_share"])

    fcst["ds"] = fcst["ds"].astype(str)
    log.info(f"  Q1: {len(monthly)} monthly rows | {len(weekly)} weekly rows | "
             f"{int(sku_q2_total['top20_flag'].sum())} top-SKU")
    return {"monthly": monthly, "weekly": weekly, "sku_q2": sku_q2,
            "daily": fcst}


# ═══════════════════════════════════════════════════════════════════
# CÂU HỎI 2 — Dự báo màu sắc & phát hiện SKU bán chậm
# ═══════════════════════════════════════════════════════════════════

def run_q2_color_demand(fact: pd.DataFrame, fcst_monthly: pd.DataFrame) -> dict:
    """
    - Seasonal color trend: so sánh tỷ trọng màu Q1-2025 vs Q1-2026
    - K-Means clustering SKU → fast/slow mover (từ beckyydo/retail-machine-learning)
    - Color Q2 forecast: apply share Q1-2026 lên Prophet yhat Q2
    - Slow-mover flag: YoY < -10% hoặc nằm cụm "Dog"
    Returns: {
        'color_q2':      DataFrame — màu × tháng Q2 với predicted_revenue + seasonal_trend,
        'color_history': DataFrame — lịch sử tỷ trọng màu,
        'sku_cluster':   DataFrame — SKU cluster + slow_mover_risk,
    }
    """
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    VALID_GROUPS = {"CITYBIKE_P", "KIDBIKE_1", "KIDBIKE_2", "SPORTBIKE_A", "SPORTBIKE_S"}
    fact = fact.copy()
    fact = fact[fact["group_code"].isin(VALID_GROUPS)]
    fact["order_date"] = pd.to_datetime(fact["order_date"])

    # ── Lịch sử tỷ trọng màu ─────────────────────────
    color_hist = (fact.groupby(["color", "group_code", "fiscal_year", "fiscal_month"])
                  .agg(revenue=("line_total","sum"), quantity=("quantity","sum"))
                  .reset_index())
    color_hist["ym"] = color_hist.apply(
        lambda r: f"{int(r.fiscal_year)}-{int(r.fiscal_month):02d}", axis=1)
    tot = color_hist.groupby(["fiscal_year", "fiscal_month"])["revenue"].sum().rename("_tot")
    color_hist = color_hist.merge(tot, on=["fiscal_year", "fiscal_month"], how="left")
    color_hist["color_share_pct"] = (color_hist["revenue"] / color_hist["_tot"] * 100).round(2)
    color_hist.drop(columns=["_tot"], inplace=True)

    # ── Seasonal trend: Q1-2025 vs Q1-2026 per màu ───
    q1_25 = (color_hist[(color_hist.fiscal_year == 2025) & (color_hist.fiscal_month <= 3)]
             .groupby("color")["color_share_pct"].mean().rename("share_q1_2025"))
    q1_26 = (color_hist[(color_hist.fiscal_year == 2026) & (color_hist.fiscal_month <= 3)]
             .groupby("color")["color_share_pct"].mean().rename("share_q1_2026"))
    color_trend = pd.concat([q1_25, q1_26], axis=1).fillna(0).reset_index()
    color_trend["yoy_share_chg"] = (color_trend["share_q1_2026"] - color_trend["share_q1_2025"]).round(2)

    def _trend_label(chg):
        if chg > 0.5:  return "Tăng nhu cầu"
        if chg < -0.5: return "Giảm nhu cầu"
        return "Ổn định"

    color_trend["seasonal_trend"] = color_trend["yoy_share_chg"].apply(_trend_label)

    # ── Color Q2 forecast ─────────────────────────────
    q1_26_share = (color_hist[color_hist.fiscal_year == 2026]
                   .groupby(["color", "group_code"])["color_share_pct"].mean().reset_index()
                   .rename(columns={"color_share_pct": "avg_share_q1_2026_pct"}))

    fcst_q2 = fcst_monthly[
        (fcst_monthly.fiscal_year == 2026) &
        fcst_monthly.fiscal_month.isin([4, 5, 6])].copy()

    color_q2 = q1_26_share.merge(
        fcst_q2[["fiscal_month", "group_code", "yhat", "split"]].rename(
            columns={"yhat": "group_yhat"}),
        on="group_code", how="left")
    color_q2["predicted_revenue"] = (
        color_q2["avg_share_q1_2026_pct"] / 100 * color_q2["group_yhat"]).round(0)

    # Gắn seasonal_trend vào
    color_q2 = color_q2.merge(
        color_trend[["color", "seasonal_trend", "yoy_share_chg"]], on="color", how="left")
    color_q2["ym"] = color_q2["fiscal_month"].apply(lambda m: f"2026-{int(m):02d}")

    # ── K-Means clustering SKU (từ beckyydo) ─────────
    sku_agg = (fact.groupby(["product_code", "product_name", "color", "group_code"])
               .agg(
                   revenue=("line_total","sum"),
                   quantity=("quantity","sum"),
                   n_orders=("so_number","nunique"),
                   n_months_active=("ym","nunique"),
               ).reset_index())

    rev_by_yr = {}
    for yr in [2025, 2026]:
        sub = (fact[fact.fiscal_year == yr]
               .groupby("product_code")["line_total"].sum().rename(f"rev_{yr}"))
        rev_by_yr[yr] = sub
    sku_agg = sku_agg.merge(rev_by_yr[2025].reset_index(), on="product_code", how="left")
    sku_agg = sku_agg.merge(rev_by_yr[2026].reset_index(), on="product_code", how="left")
    sku_agg["rev_2025"] = sku_agg["rev_2025"].fillna(0)
    sku_agg["rev_2026"] = sku_agg["rev_2026"].fillna(0)
    sku_agg["rev_2026_ann"] = sku_agg["rev_2026"] * 4
    sku_agg["yoy_rev_pct"]  = ((sku_agg["rev_2026_ann"] - sku_agg["rev_2025"]) /
                                sku_agg["rev_2025"].replace(0, np.nan) * 100).fillna(0)
    sku_agg["avg_monthly_rev"] = sku_agg["revenue"] / sku_agg["n_months_active"].replace(0, 1)

    features = ["revenue", "quantity", "n_orders", "n_months_active", "yoy_rev_pct", "avg_monthly_rev"]
    X = sku_agg[features].fillna(0)
    scaler = StandardScaler()
    X_sc = scaler.fit_transform(X)

    km = KMeans(n_clusters=4, random_state=42, n_init=10)
    sku_agg["cluster"] = km.fit_predict(X_sc)

    # Map cluster → label dựa theo doanh thu trung bình
    cluster_rev = sku_agg.groupby("cluster")["revenue"].mean().sort_values(ascending=False)
    cluster_labels = {
        cluster_rev.index[0]: "Ngôi sao",
        cluster_rev.index[1]: "Bò sữa",
        cluster_rev.index[2]: "Dấu hỏi",
        cluster_rev.index[3]: "Bán chậm",
    }
    sku_agg["sku_cluster_label"] = sku_agg["cluster"].map(cluster_labels)

    # Slow-mover: cluster Bán chậm HOẶC YoY < -10%
    sku_agg["slow_mover_risk"] = np.where(
        (sku_agg["sku_cluster_label"] == "Bán chậm") | (sku_agg["yoy_rev_pct"] < -10),
        "Nguy cơ cao",
        np.where(sku_agg["yoy_rev_pct"] < 0, "Theo dõi", "Ổn định")
    )

    log.info(f"  Q2: {len(color_q2)} color forecast rows | "
             f"{(sku_agg['slow_mover_risk']=='Nguy cơ cao').sum()} slow-mover SKU")
    return {
        "color_q2":      color_q2,
        "color_history": color_hist,
        "sku_cluster":   sku_agg,
    }


# ═══════════════════════════════════════════════════════════════════
# CÂU HỎI 3 — Dự báo hoạt động đại lý
# ═══════════════════════════════════════════════════════════════════

def run_q3_dealer_forecast(fact: pd.DataFrame) -> dict:
    """
    - BG-NBD: xác suất đặt hàng trong 30 ngày tới (từ mukulsinghal001/clv)
    - LightGBM churn: P(churn) + SHAP feature importance (từ jamiubadmusng/churn)
    - Điểm xu hướng mua hàng (trend_score) + mức độ ưu tiên tiếp thị
    Returns: {
        'dealer_activity': DataFrame — mỗi đại lý + BG-NBD prob + LightGBM churn + priority,
        'shap_importance': DataFrame — top feature importances,
        'dealer_churn':    DataFrame — churn labels + proba + split,
    }
    """
    from lifetimes import BetaGeoFitter
    from lifetimes.utils import summary_data_from_transaction_data
    import lightgbm as lgb
    import shap
    from sklearn.model_selection import StratifiedShuffleSplit
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.linear_model import LogisticRegression

    fact = fact.copy()
    fact["order_date"] = pd.to_datetime(fact["order_date"])

    FEAT_END = pd.Timestamp("2025-03-31")
    REF_DATE = pd.Timestamp("2026-03-31")

    # ── BG-NBD: xác suất mua trong 30 ngày tới ───────
    # Dùng toàn bộ lịch sử giao dịch để fit
    rfm_data = summary_data_from_transaction_data(
        fact[fact.customer_code.str.len() > 0],
        customer_id_col="customer_code",
        datetime_col="order_date",
        monetary_value_col="line_total",
        observation_period_end=REF_DATE,
        freq="D",
    )
    rfm_data = rfm_data[rfm_data["frequency"] > 0].copy()

    bgf = BetaGeoFitter(penalizer_coef=0.01)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        bgf.fit(rfm_data["frequency"], rfm_data["recency"], rfm_data["T"])

    rfm_data["prob_purchase_30d"] = bgf.conditional_probability_alive(
        rfm_data["frequency"], rfm_data["recency"], rfm_data["T"])
    rfm_data["expected_orders_30d"] = bgf.conditional_expected_number_of_purchases_up_to_time(
        30, rfm_data["frequency"], rfm_data["recency"], rfm_data["T"]).round(3)
    rfm_data = rfm_data.reset_index()

    log.info(f"  BG-NBD fit: {len(rfm_data)} đại lý")

    # ── Feature engineering Q1-2025 ──────────────────
    q1_2025 = fact[fact.order_date <= FEAT_END]
    active_2026 = set(fact[fact.order_date >= "2026-01-01"]["customer_code"].unique())
    cust_meta = (fact[["customer_code", "customer_name", "province_name", "region"]]
                 .drop_duplicates("customer_code").set_index("customer_code"))

    feats = []
    for cc, g in q1_2025.groupby("customer_code"):
        g = g.sort_values("order_date")
        last = g["order_date"].max()
        monthly_rev = g.groupby(g["order_date"].dt.to_period("M"))["line_total"].sum()
        slope = 0.0
        if len(monthly_rev) >= 2:
            slope = float(np.polyfit(np.arange(len(monthly_rev)), monthly_rev.values, 1)[0])
        m = cust_meta.loc[cc] if cc in cust_meta.index else pd.Series()
        # Extra features (từ jamiubadmusng — 24 features)
        total_rev = fact[fact.customer_code == cc]["line_total"].sum()
        n_groups  = g["group_code"].nunique()
        cancel_rate = 0.0  # không có dữ liệu cancel trong dataset này
        feats.append({
            "customer_code":       cc,
            "customer_name":       m.get("customer_name", ""),
            "province_name":       m.get("province_name", ""),
            "region":              m.get("region", ""),
            "recency_days":        (FEAT_END - last).days,
            "n_orders_q1_2025":    g["so_number"].nunique(),
            "revenue_q1_2025":     int(g["line_total"].sum()),
            "avg_order_value":     round(g.groupby("so_number")["line_total"].sum().mean(), 0),
            "n_product_groups":    n_groups,
            "trend_slope":         round(slope, 2),
            "revenue_total":       int(total_rev),
            "n_orders_total":      fact[fact.customer_code == cc]["so_number"].nunique(),
            "groups_bought":       "|".join(sorted(g["group_code"].dropna().unique())),
            "n_orders_q1_2026":    fact[(fact.customer_code == cc) &
                                        (fact.order_date >= "2026-01-01")]["so_number"].nunique(),
            "revenue_q1_2026":     int(fact[(fact.customer_code == cc) &
                                            (fact.order_date >= "2026-01-01")]["line_total"].sum()),
            "active_in_t3":        int((fact[(fact.customer_code == cc)]["order_date"] >= "2026-03-01").any()),
        })

    cdf = pd.DataFrame(feats)
    cdf["churn_label"] = (~cdf["customer_code"].isin(active_2026)).astype(int)

    # ── RFM scores ────────────────────────────────────
    for col, sc, asc in [("recency_days","rfm_r",True),
                          ("n_orders_q1_2025","rfm_f",False),
                          ("revenue_q1_2025","rfm_m",False)]:
        rk = cdf[col].rank(pct=True, method="average")
        bins, labels = [0,.2,.4,.6,.8,1.0], ([5,4,3,2,1] if asc else [1,2,3,4,5])
        cdf[sc] = pd.cut(rk, bins=bins, labels=labels, include_lowest=True).astype(int)

    def _rfm_seg(r, f, m):
        if r>=4 and f>=4 and m>=4: return "Khách hàng tiêu biểu"
        if r>=4 and f>=3:           return "Khách hàng trung thành"
        if r>=4:                    return "Khách hàng mới tiềm năng"
        if r<=2 and f>=4:           return "Cần chăm sóc đặc biệt"
        if r<=2:                    return "Có nguy cơ rời bỏ"
        return "Cần theo dõi"

    cdf["rfm_segment"] = cdf.apply(lambda r: _rfm_seg(r.rfm_r, r.rfm_f, r.rfm_m), axis=1)

    # ── LightGBM churn (từ jamiubadmusng) ────────────
    # active_in_t3, revenue_total, n_orders_total bị loại — dùng data 2026 → data leakage
    X_cols = ["recency_days","n_orders_q1_2025","revenue_q1_2025",
              "avg_order_value","n_product_groups","trend_slope"]
    X = cdf[X_cols].fillna(0).values
    y = cdf["churn_label"].values

    sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr_idx, te_idx = next(sss.split(X, y))

    lgb_model = lgb.LGBMClassifier(
        n_estimators=200, learning_rate=0.05, max_depth=4,
        num_leaves=15, min_child_samples=10,
        subsample=0.8, colsample_bytree=0.8,
        random_state=42, verbose=-1,
    )
    lgb_model.fit(X[tr_idx], y[tr_idx],
                  eval_set=[(X[te_idx], y[te_idx])],
                  callbacks=[lgb.early_stopping(20, verbose=False),
                             lgb.log_evaluation(period=-1)])

    cdf["churn_prob"]  = lgb_model.predict_proba(X)[:, 1].round(4)
    cdf["churn_split"] = "train"
    cdf.loc[cdf.index[te_idx], "churn_split"] = "test"
    cdf["churn_priority"] = pd.cut(cdf["churn_prob"], bins=[0,.3,.6,1.0],
                                    labels=["Thấp","Trung bình","Cao"],
                                    include_lowest=True)
    roc_te = roc_auc_score(y[te_idx], lgb_model.predict_proba(X[te_idx])[:, 1])
    cdf["roc_auc_test"] = round(roc_te, 4)
    log.info(f"  LightGBM churn ROC-AUC test: {roc_te:.3f}")

    # ── SHAP feature importance (từ jamiubadmusng) ───
    explainer = shap.TreeExplainer(lgb_model)
    shap_values = explainer.shap_values(X)
    sv = shap_values[1] if isinstance(shap_values, list) else shap_values
    shap_imp = pd.DataFrame({
        "feature":    X_cols,
        "shap_mean_abs": np.abs(sv).mean(axis=0).round(4),
    }).sort_values("shap_mean_abs", ascending=False).reset_index(drop=True)
    shap_imp["rank"] = shap_imp.index + 1
    log.info(f"  SHAP top feature: {shap_imp.iloc[0]['feature']} "
             f"(importance={shap_imp.iloc[0]['shap_mean_abs']:.4f})")

    # ── Trend score + marketing priority ─────────────
    # Normalize trend_slope → 0–100
    ts = cdf["trend_slope"].fillna(0)
    ts_min, ts_max = ts.min(), ts.max()
    cdf["trend_score"] = ((ts - ts_min) / (ts_max - ts_min + 1e-9) * 100).round(1)

    # Marketing priority: 1=Ưu tiên cao (churn cao + có xu hướng mua giảm)
    #                     2=Trung bình, 3=Thấp
    def _priority(row):
        if row.churn_prob >= 0.6 and row.trend_score < 40: return 1
        if row.churn_prob >= 0.4 or row.trend_score < 30:  return 2
        return 3
    cdf["marketing_priority"]      = cdf.apply(_priority, axis=1)
    cdf["marketing_priority_label"] = cdf["marketing_priority"].map(
        {1:"Ưu tiên cao", 2:"Trung bình", 3:"Thấp"})

    # ── Gộp BG-NBD vào ───────────────────────────────
    dealer_activity = cdf.merge(
        rfm_data[["customer_code","prob_purchase_30d","expected_orders_30d"]],
        on="customer_code", how="left")
    dealer_activity["prob_purchase_30d"]   = dealer_activity["prob_purchase_30d"].round(4)
    dealer_activity["expected_orders_30d"] = dealer_activity["expected_orders_30d"].fillna(0)

    # Unified activity_risk từ BG-NBD
    dealer_activity["activity_risk"] = pd.cut(
        dealer_activity["prob_purchase_30d"].fillna(0),
        bins=[0, .3, .6, 1.0],
        labels=["Nguy cơ cao","Trung bình","Tích cực"],
        include_lowest=True)
    dealer_activity["priority_contact"] = (dealer_activity["prob_purchase_30d"].fillna(0) < 0.3).astype(int)

    # ── Churn output riêng ────────────────────────────
    churn_cols = ["customer_code","churn_label","churn_prob","churn_priority",
                  "churn_split","roc_auc_test"]
    dealer_churn = cdf[churn_cols].copy()

    log.info(f"  Q3: {len(dealer_activity)} đại lý | "
             f"BG-NBD prob_purchase_30d: mean={dealer_activity['prob_purchase_30d'].mean():.3f} | "
             f"priority_contact: {dealer_activity['priority_contact'].sum()}")

    return {
        "dealer_activity": dealer_activity,
        "shap_importance": shap_imp,
        "dealer_churn":    dealer_churn,
    }
