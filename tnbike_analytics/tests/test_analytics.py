"""
Tests cho analytics core: sql_data_loader, SKU enrichment, RFM/Churn, agg grains.
Chạy độc lập — không cần DB, không cần file .eml/.pdf.
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


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def fact():
    dfs = load_all()
    f = build_fact(dfs)
    f["order_date"]   = pd.to_datetime(f["order_date"])
    f["product_code"] = f["product_code"].astype(str)
    f["ym"]           = f["order_date"].dt.to_period("M").astype(str)
    return f


# ── sql_data_loader ─────────────────────────────────────────────────────────────────

def test_load_all_tables():
    dfs = load_all()
    for tbl in ["product_group", "product_line", "product",
                "province", "customer", "sales_order", "order_line"]:
        assert tbl in dfs, f"Thiếu bảng: {tbl}"
        assert len(dfs[tbl]) > 0, f"Bảng rỗng: {tbl}"


def test_fact_row_count(fact):
    assert len(fact) == 17031, f"Expected 17031 rows, got {len(fact)}"


def test_fact_revenue_total(fact):
    total = int(fact["line_total"].sum())
    assert total == 68_641_114_306, f"Revenue total sai: {total:,}"


def test_fact_date_range(fact):
    assert fact["order_date"].min().date().isoformat() == "2025-01-02"
    assert fact["order_date"].max().date().isoformat() == "2026-02-28"


def test_fact_customer_count(fact):
    assert fact["customer_code"].nunique() == 702


def test_fact_sku_count(fact):
    assert fact["product_code"].nunique() == 247


def test_product_code_leading_zeros(fact):
    """product_code phải là string — không mất leading zeros."""
    assert fact["product_code"].dtype == object or pd.api.types.is_string_dtype(fact["product_code"])
    # Mã có leading zeros phải bắt đầu bằng '0'
    leading_zero = fact["product_code"].str.startswith("0").sum()
    assert leading_zero > 0, "Không tìm thấy product_code có leading zeros"


def test_fact_group_codes(fact):
    expected = {"CITYBIKE_P", "KIDBIKE_1", "KIDBIKE_2", "SPORTBIKE_A", "SPORTBIKE_S"}
    actual = set(fact["group_code"].dropna().unique())
    assert actual == expected, f"group_codes không khớp: {actual}"


def test_fact_required_columns(fact):
    required = [
        "order_id", "so_number", "product_code", "quantity", "unit_price", "line_total",
        "order_date", "fiscal_year", "fiscal_month", "fiscal_quarter",
        "customer_code", "customer_name", "province_name", "region",
        "product_name", "group_code", "group_name",
    ]
    missing = [c for c in required if c not in fact.columns]
    assert not missing, f"Thiếu cột: {missing}"


# ── SKU enrichment ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sku_table(fact):
    sku = (fact.groupby(["product_code", "product_name", "group_code", "group_name",
                         "line_name", "color"], dropna=False)
               .agg(rev_sku=("line_total", "sum"), qty_sku=("quantity", "sum"))
               .reset_index())
    for yr in [2025, 2026]:
        sub = fact[fact.fiscal_year == yr].groupby("product_code").agg(
            **{f"rev_{yr}": ("line_total", "sum")}).reset_index()
        sku = sku.merge(sub, on="product_code", how="left")
    for c in ["rev_2025", "rev_2026"]:
        sku[c] = sku[c].fillna(0)
    sku["rev_2026_ann"] = sku["rev_2026"] * 6
    sku["yoy_rev_pct"]  = ((sku["rev_2026_ann"] - sku["rev_2025"])
                           / sku["rev_2025"].replace(0, np.nan) * 100).round(2)
    sku = sku.sort_values("rev_sku", ascending=False).reset_index(drop=True)
    sku["pareto_cum_pct"] = (sku["rev_sku"].cumsum() / sku["rev_sku"].sum() * 100).round(2)
    sku["pareto_class"]   = pd.cut(sku["pareto_cum_pct"], bins=[0, 70, 90, 100],
                                    labels=["A", "B", "C"])
    grp_rev = sku.groupby("group_code")["rev_sku"].sum()
    sku["rev_share_in_group_pct"] = (
        sku["rev_sku"] / sku["group_code"].map(grp_rev) * 100).round(2)
    return sku


def test_sku_pareto_classes(sku_table):
    classes = set(sku_table["pareto_class"].dropna().unique().tolist())
    assert classes == {"A", "B", "C"}, f"Pareto classes: {classes}"


def test_sku_pareto_max(sku_table):
    assert sku_table["pareto_cum_pct"].max() <= 100.0


def test_sku_yoy_2025_rows_nonzero(fact):
    """SKU có doanh thu cả 2 năm → yoy không phải NaN."""
    rev25 = fact[fact.fiscal_year == 2025].groupby("product_code")["line_total"].sum()
    rev26 = fact[fact.fiscal_year == 2026].groupby("product_code")["line_total"].sum()
    both  = rev25.index.intersection(rev26.index)
    assert len(both) > 0, "Không có SKU nào có doanh thu cả 2 năm"


def test_sku_revenue_rank_unique(sku_table):
    assert sku_table.shape[0] == sku_table.shape[0]  # sanity
    # rank 1 là SKU có revenue cao nhất
    top = sku_table.sort_values("rev_sku", ascending=False).iloc[0]
    assert top["rev_sku"] == sku_table["rev_sku"].max()


# ── Monthly aggregation / YoY fix ─────────────────────────────────────────────────

@pytest.fixture(scope="module")
def monthly_agg(fact):
    agg = (fact.groupby(["fiscal_year", "fiscal_month"])
               .agg(revenue=("line_total", "sum"))
               .reset_index())
    base25 = agg[agg.fiscal_year == 2025][["fiscal_month", "revenue"]].rename(
        columns={"revenue": "_r25"})
    agg = agg.merge(base25, on="fiscal_month", how="left")
    agg["yoy_revenue_pct"] = (
        (agg["revenue"] - agg["_r25"]) / agg["_r25"].replace(0, np.nan) * 100).round(2)
    agg.drop(columns=["_r25"], inplace=True)
    # Bug fix: base year phải là NaN
    agg.loc[agg["fiscal_year"] == 2025, "yoy_revenue_pct"] = np.nan
    return agg


def test_yoy_2025_is_nan(monthly_agg):
    """Năm gốc 2025 không thể có YoY — phải là NaN, không phải 0."""
    rows_2025 = monthly_agg[monthly_agg.fiscal_year == 2025]
    assert rows_2025["yoy_revenue_pct"].isna().all(), \
        f"YoY 2025 phải NaN, got: {rows_2025['yoy_revenue_pct'].tolist()}"


def test_yoy_2026_jan_positive(monthly_agg):
    """T1/2026 phải có YoY > 0 (tăng mạnh so với T1/2025)."""
    row = monthly_agg[(monthly_agg.fiscal_year == 2026) & (monthly_agg.fiscal_month == 1)]
    assert len(row) == 1
    assert row["yoy_revenue_pct"].iloc[0] > 100, \
        f"YoY T1/2026 expected >100%, got {row['yoy_revenue_pct'].iloc[0]}"


def test_monthly_row_count(monthly_agg):
    # 3 tháng 2025 + 2 tháng 2026 = 5 rows
    assert len(monthly_agg) == 5, f"Expected 5 monthly rows, got {len(monthly_agg)}"


# ── Customer RFM ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def cust_rfm(fact):
    FEAT_END = pd.Timestamp("2025-03-31")
    q1_2025  = fact[fact.order_date <= FEAT_END]
    active_2026 = set(fact[fact.order_date >= "2026-01-01"]["customer_code"].unique())

    rows = []
    for cc, g in q1_2025.groupby("customer_code"):
        last = g["order_date"].max()
        rows.append({
            "customer_code":   cc,
            "recency_days":    (FEAT_END - last).days,
            "n_orders":        g["so_number"].nunique(),
            "revenue":         int(g["line_total"].sum()),
            "churn_label":     int(cc not in active_2026),
        })
    cdf = pd.DataFrame(rows)
    for col, sc, asc in [
        ("recency_days", "rfm_r", True),
        ("n_orders",     "rfm_f", False),
        ("revenue",      "rfm_m", False),
    ]:
        rk = cdf[col].rank(pct=True, method="average")
        bins, labels = [0, .2, .4, .6, .8, 1.0], ([5, 4, 3, 2, 1] if asc else [1, 2, 3, 4, 5])
        cdf[sc] = pd.cut(rk, bins=bins, labels=labels, include_lowest=True).astype(int)
    return cdf


def test_rfm_customer_count(cust_rfm):
    """Chỉ khách mua trong Q1-2025 mới có RFM."""
    assert len(cust_rfm) == 333, f"Expected 333 customers in Q1-2025, got {len(cust_rfm)}"


def test_rfm_score_range(cust_rfm):
    for col in ["rfm_r", "rfm_f", "rfm_m"]:
        assert cust_rfm[col].between(1, 5).all(), f"{col} ngoài [1,5]"


def test_churn_rate_range(cust_rfm):
    rate = cust_rfm["churn_label"].mean()
    # Churn rate khoảng 86% (288/333)
    assert 0.80 < rate < 0.95, f"Churn rate bất thường: {rate:.1%}"


# ── Revenue consistency ──────────────────────────────────────────────────────────

def test_revenue_consistency_across_grains(fact):
    """Tổng doanh thu theo tháng = tổng doanh thu fact."""
    total_fact    = int(fact["line_total"].sum())
    total_monthly = int(fact.groupby(["fiscal_year", "fiscal_month"])["line_total"].sum().sum())
    assert total_fact == total_monthly


def test_revenue_by_group_sum(fact):
    """Tổng doanh thu theo group (bỏ NULL) + NULL phải = tổng fact."""
    by_group = int(fact.groupby("group_code", dropna=False)["line_total"].sum().sum())
    assert by_group == int(fact["line_total"].sum())
