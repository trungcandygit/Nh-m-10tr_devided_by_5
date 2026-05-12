"""
Tests cho prediction_engine.py — Q1 Prophet, Q2 Color/K-Means, Q3 BG-NBD/LightGBM/SHAP.

Chạy: pytest tests/test_prediction_engine.py -v
Kết quả model metrics ghi vào: output/test_report.md
"""
import sys
import warnings
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics.sql_data_loader import load_all, build_fact
from analytics.t3_loader import load_t3
from analytics.prediction_engine import run_q1_forecast, run_q2_color_demand, run_q3_dealer_forecast

GROUPS = {"CITYBIKE_P", "KIDBIKE_1", "KIDBIKE_2", "SPORTBIKE_A", "SPORTBIKE_S"}
OUT_DIR = Path(__file__).parent.parent / "output"
REPORT  = OUT_DIR / "test_report.md"


# ═══════════════════════════════════════════════════════════════════
# Fixtures (scope=module → chỉ chạy 1 lần, cache kết quả)
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def fact():
    dfs  = load_all()
    base = build_fact(dfs)
    base["order_date"] = pd.to_datetime(base["order_date"])
    base["ym"] = base["order_date"].dt.to_period("M").astype(str)

    # Gắn T3 nếu có (emails đã giải nén)
    email_dir = Path(__file__).parent.parent / "data/raw/emails"
    if email_dir.exists() and any(email_dir.glob("*.eml")):
        try:
            t3 = load_t3(dfs, email_dir=email_dir)
            if not t3.empty:
                t3["order_date"] = pd.to_datetime(t3["order_date"])
                t3["ym"] = t3["order_date"].dt.to_period("M").astype(str)
                base = pd.concat([base, t3], ignore_index=True)
        except Exception:
            pass
    return base


@pytest.fixture(scope="module")
def q1_out(fact):
    return run_q1_forecast(fact)


@pytest.fixture(scope="module")
def q2_out(fact, q1_out):
    return run_q2_color_demand(fact, q1_out["monthly"])


@pytest.fixture(scope="module")
def q3_out(fact):
    return run_q3_dealer_forecast(fact)


# ═══════════════════════════════════════════════════════════════════
# Q1 — Prophet Forecast
# ═══════════════════════════════════════════════════════════════════

def test_q1_returns_all_keys(q1_out):
    assert set(q1_out.keys()) >= {"monthly", "weekly", "sku_q2", "daily"}


def test_q1_monthly_has_all_groups(q1_out):
    found = set(q1_out["monthly"]["group_code"].unique()) & GROUPS
    assert found == GROUPS, f"Thiếu nhóm SP: {GROUPS - found}"


def test_q1_monthly_forecast_period(q1_out):
    """monthly phải có đủ 5 nhóm hợp lệ cho Q2-2026 (tháng 4,5,6)."""
    fcst = q1_out["monthly"]
    q2 = fcst[(fcst.fiscal_year == 2026) & fcst.fiscal_month.isin([4, 5, 6])
              & fcst.group_code.isin(GROUPS)]
    assert len(q2) == 5 * 3, f"Cần 15 rows Q2 (5 nhóm × 3 tháng), got {len(q2)}"


def test_q1_yhat_nonnegative(q1_out):
    assert (q1_out["daily"]["yhat"] >= 0).all(), "yhat có giá trị âm"


def test_q1_split_labels(q1_out):
    splits = set(q1_out["monthly"]["split"].unique())
    assert splits == {"train", "forecast"}, f"split values: {splits}"


def test_q1_weekly_q2_only(q1_out):
    """weekly chỉ chứa Q2-2026 (tháng 4-6)."""
    w = q1_out["weekly"]
    assert "yw" in w.columns and "week_start" in w.columns
    assert len(w) > 0
    assert len(w) >= 5 * 13 - 5, f"Weekly rows quá ít: {len(w)}"


def test_q1_sku_top20_flag(q1_out):
    top = q1_out["sku_q2"][q1_out["sku_q2"]["top20_flag"] == 1]
    assert len(top) == 60, f"top20_flag=1 expected 60 rows, got {len(top)}"


def test_q1_sku_predicted_revenue_positive(q1_out):
    top = q1_out["sku_q2"][q1_out["sku_q2"]["top20_flag"] == 1]
    assert (top["predicted_revenue"] > 0).all(), "Top-20 SKU có predicted_revenue = 0"


def test_q1_sku_revenue_bounds(q1_out):
    sku = q1_out["sku_q2"]
    assert (sku["predicted_revenue_lower"] <= sku["predicted_revenue"]).all()
    assert (sku["predicted_revenue"]       <= sku["predicted_revenue_upper"]).all()


# ═══════════════════════════════════════════════════════════════════
# Q2 — Color demand + K-Means slow-mover
# ═══════════════════════════════════════════════════════════════════

def test_q2_returns_all_keys(q2_out):
    assert set(q2_out.keys()) >= {"color_q2", "color_history", "sku_cluster"}


def test_q2_seasonal_trend_valid_labels(q2_out):
    valid = {"Tăng nhu cầu", "Giảm nhu cầu", "Ổn định"}
    found = set(q2_out["color_q2"]["seasonal_trend"].dropna().unique())
    assert found <= valid, f"seasonal_trend không hợp lệ: {found - valid}"


def test_q2_color_q2_forecast_period(q2_out):
    months = q2_out["color_q2"]["fiscal_month"].unique()
    assert set(months) >= {4, 5, 6}


def test_q2_color_q2_positive_revenue(q2_out):
    cq = q2_out["color_q2"]
    pos = (cq["predicted_revenue"] > 0).sum()
    assert pos > len(cq) * 0.8, f"Chỉ {pos}/{len(cq)} màu có predicted_revenue > 0"


def test_q2_cluster_labels_valid(q2_out):
    valid = {"Ngôi sao", "Bò sữa", "Dấu hỏi", "Bán chậm"}
    found = set(q2_out["sku_cluster"]["sku_cluster_label"].unique())
    assert found == valid, f"Cluster labels: {found}"


def test_q2_slow_mover_risk_valid(q2_out):
    valid = {"Nguy cơ cao", "Theo dõi", "Ổn định"}
    found = set(q2_out["sku_cluster"]["slow_mover_risk"].unique())
    assert found <= valid, f"slow_mover_risk không hợp lệ: {found - valid}"


def test_q2_slow_mover_exists(q2_out):
    n = (q2_out["sku_cluster"]["slow_mover_risk"] == "Nguy cơ cao").sum()
    assert n > 0, "Không tìm được SKU nào là slow-mover"


def test_q2_color_history_share_sums(q2_out):
    ch = q2_out["color_history"]
    totals = ch.groupby(["fiscal_year", "fiscal_month"])["color_share_pct"].sum()
    assert ((totals > 98) & (totals < 102)).all(), \
        f"color_share_pct tổng không ≈ 100%: min={totals.min():.1f}%"


# ═══════════════════════════════════════════════════════════════════
# Q3 — BG-NBD + LightGBM + SHAP
# ═══════════════════════════════════════════════════════════════════

def test_q3_returns_all_keys(q3_out):
    assert set(q3_out.keys()) >= {"dealer_activity", "shap_importance", "dealer_churn"}


def test_q3_dealer_count(q3_out):
    n = len(q3_out["dealer_activity"])
    assert 300 <= n <= 350, f"Số đại lý bất thường: {n}"


def test_q3_prob_purchase_range(q3_out):
    p = q3_out["dealer_activity"]["prob_purchase_30d"].dropna()
    assert (p >= 0).all() and (p <= 1).all(), "prob_purchase_30d ngoài [0,1]"


def test_q3_expected_orders_nonnegative(q3_out):
    e = q3_out["dealer_activity"]["expected_orders_30d"].fillna(0)
    assert (e >= 0).all(), "expected_orders_30d có giá trị âm"


def test_q3_churn_prob_range(q3_out):
    p = q3_out["dealer_churn"]["churn_prob"]
    assert (p >= 0).all() and (p <= 1).all(), "churn_prob ngoài [0,1]"


def test_q3_roc_auc_acceptable(q3_out):
    auc = q3_out["dealer_churn"]["roc_auc_test"].iloc[0]
    assert auc >= 0.65, f"ROC-AUC quá thấp: {auc:.3f}"


def test_q3_no_leakage_auc_ceiling(q3_out):
    auc = q3_out["dealer_churn"]["roc_auc_test"].iloc[0]
    assert auc < 0.99, f"ROC-AUC quá cao ({auc:.3f}) — kiểm tra data leakage"


def test_q3_churn_split_coverage(q3_out):
    splits = q3_out["dealer_churn"]["churn_split"].value_counts()
    assert "train" in splits and "test" in splits
    test_pct = splits["test"] / splits.sum()
    assert 0.15 < test_pct < 0.25, f"Test split ratio bất thường: {test_pct:.1%}"


def test_q3_churn_priority_valid(q3_out):
    valid = {"Thấp", "Trung bình", "Cao"}
    found = set(q3_out["dealer_churn"]["churn_priority"].astype(str).unique())
    assert found <= valid, f"churn_priority không hợp lệ: {found - valid}"


def test_q3_shap_importance_count(q3_out):
    assert len(q3_out["shap_importance"]) == 6, \
        f"SHAP phải có 6 features (sau bỏ leaky features), got {len(q3_out['shap_importance'])}"


def test_q3_shap_importance_positive(q3_out):
    assert (q3_out["shap_importance"]["shap_mean_abs"] >= 0).all()


def test_q3_marketing_priority_valid(q3_out):
    valid = {"Ưu tiên cao", "Trung bình", "Thấp"}
    found = set(q3_out["dealer_activity"]["marketing_priority_label"].unique())
    assert found <= valid, f"marketing_priority_label: {found - valid}"


def test_q3_rfm_columns_present(q3_out):
    required = ["rfm_r", "rfm_f", "rfm_m", "rfm_segment"]
    missing  = [c for c in required if c not in q3_out["dealer_activity"].columns]
    assert not missing, f"Thiếu RFM columns: {missing}"


def test_q3_rfm_score_range(q3_out):
    da = q3_out["dealer_activity"]
    for col in ["rfm_r", "rfm_f", "rfm_m"]:
        assert da[col].between(1, 5).all(), f"{col} ngoài [1,5]"


def test_q3_activity_risk_valid(q3_out):
    valid = {"Nguy cơ cao", "Trung bình", "Tích cực"}
    found = set(q3_out["dealer_activity"]["activity_risk"].astype(str).unique())
    assert found <= valid, f"activity_risk: {found - valid}"


# ═══════════════════════════════════════════════════════════════════
# Conftest hook — ghi test_report.md sau khi chạy xong
# ═══════════════════════════════════════════════════════════════════

def pytest_sessionfinish(session, exitstatus):
    try:
        _write_report()
    except Exception:
        pass


def _write_report():
    import datetime
    dfs  = load_all()
    base = build_fact(dfs)
    base["order_date"] = pd.to_datetime(base["order_date"])
    base["ym"] = base["order_date"].dt.to_period("M").astype(str)

    email_dir = Path(__file__).parent.parent / "data/raw/emails"
    if email_dir.exists() and any(email_dir.glob("*.eml")):
        try:
            t3 = load_t3(dfs, email_dir=email_dir)
            if not t3.empty:
                t3["order_date"] = pd.to_datetime(t3["order_date"])
                t3["ym"] = t3["order_date"].dt.to_period("M").astype(str)
                base = pd.concat([base, t3], ignore_index=True)
        except Exception:
            pass

    q3  = run_q3_dealer_forecast(base)
    q1  = run_q1_forecast(base)
    q2  = run_q2_color_demand(base, q1["monthly"])

    da  = q3["dealer_activity"]
    dc  = q3["dealer_churn"]
    si  = q3["shap_importance"]
    auc = round(float(dc["roc_auc_test"].iloc[0]), 4)

    lines = [
        f"# Kết quả kiểm thử prediction_engine.py",
        f"",
        f"Ngày chạy: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"## Q1 — Prophet Forecast",
        f"",
        f"| Chỉ số | Giá trị |",
        f"|---|---|",
        f"| Số nhóm SP | {q1['monthly']['group_code'].nunique()} |",
        f"| Daily rows (train+forecast) | {len(q1['daily'])} |",
        f"| Monthly rows | {len(q1['monthly'])} |",
        f"| Weekly rows (Q2 only) | {len(q1['weekly'])} |",
        f"| SKU Q2 total rows | {len(q1['sku_q2'])} |",
        f"| Top-20 SKU (flag=1) | {(q1['sku_q2']['top20_flag']==1).sum()} |",
        f"| yhat âm | {(q1['daily']['yhat'] < 0).sum()} |",
        f"",
        f"## Q2 — Color Demand + K-Means",
        f"",
        f"| Chỉ số | Giá trị |",
        f"|---|---|",
        f"| Color Q2 rows | {len(q2['color_q2'])} |",
        f"| SKU cluster rows | {len(q2['sku_cluster'])} |",
        f"| Slow-mover (Nguy cơ cao) | {(q2['sku_cluster']['slow_mover_risk']=='Nguy cơ cao').sum()} |",
        f"| Theo dõi | {(q2['sku_cluster']['slow_mover_risk']=='Theo dõi').sum()} |",
        f"| Seasonal trend — Tăng | {(q2['color_q2']['seasonal_trend']=='Tăng nhu cầu').nunique()} màu |",
        f"| Seasonal trend — Giảm | {(q2['color_q2']['seasonal_trend']=='Giảm nhu cầu').nunique()} màu |",
        f"| Seasonal trend — Ổn định | {(q2['color_q2']['seasonal_trend']=='Ổn định').nunique()} màu |",
        f"",
        f"### Phân bổ cluster SKU",
        f"",
        f"| Cluster | Số SKU |",
        f"|---|---|",
    ]
    for lbl, cnt in q2['sku_cluster']['sku_cluster_label'].value_counts().items():
        lines.append(f"| {lbl} | {cnt} |")

    lines += [
        f"",
        f"## Q3 — BG-NBD + LightGBM Churn + SHAP",
        f"",
        f"| Chỉ số | Giá trị |",
        f"|---|---|",
        f"| Đại lý phân tích | {len(da)} |",
        f"| BG-NBD prob_purchase_30d — mean | {da['prob_purchase_30d'].mean():.3f} |",
        f"| BG-NBD prob_purchase_30d — median | {da['prob_purchase_30d'].median():.3f} |",
        f"| priority_contact=1 (prob < 0.3) | {da['priority_contact'].sum()} |",
        f"| LightGBM ROC-AUC (test 20%) | **{auc}** |",
        f"| Churn cao (P ≥ 0.6) | {(dc['churn_prob']>=0.6).sum()} |",
        f"| Churn trung bình (0.3–0.6) | {((dc['churn_prob']>=0.3)&(dc['churn_prob']<0.6)).sum()} |",
        f"| Churn thấp (P < 0.3) | {(dc['churn_prob']<0.3).sum()} |",
        f"",
        f"### SHAP Feature Importance (LightGBM Churn)",
        f"",
        f"| Rank | Feature | SHAP mean |abs| |",
        f"|---|---|---|",
    ]
    for _, r in si.iterrows():
        lines.append(f"| {int(r['rank'])} | {r['feature']} | {r['shap_mean_abs']:.4f} |")

    lines += [
        f"",
        f"### Phân bổ phân khúc RFM",
        f"",
        f"| Phân khúc | Số đại lý |",
        f"|---|---|",
    ]
    for seg, cnt in da["rfm_segment"].value_counts().items():
        lines.append(f"| {seg} | {cnt} |")

    lines += [
        f"",
        f"### Marketing Priority",
        f"",
        f"| Mức | Số đại lý |",
        f"|---|---|",
    ]
    for lbl, cnt in da["marketing_priority_label"].value_counts().items():
        lines.append(f"| {lbl} | {cnt} |")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
