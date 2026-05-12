"""
Load all pre-computed CSVs from output/ into memory at startup.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent.parent
STR_COLS = {"product_code": str}

def _csv(subdir, name, **kw):
    return pd.read_csv(ROOT / "output" / subdir / name, dtype=STR_COLS, **kw)

def load_all():
    return {
        # ── data/ — dữ liệu thực tế ──────────────────────
        "kpi":           _csv("data", "kpi_overview.csv"),
        "monthly":       _csv("data", "monthly_trend.csv"),
        "sku":           _csv("data", "product_analysis.csv"),
        "color":         _csv("data", "color_analysis.csv"),
        "color_hist":    _csv("data", "color_history.csv"),
        "dealer":        _csv("data", "dealer_rfm.csv"),
        "province":      _csv("data", "geo_province.csv"),
        "region":        _csv("data", "geo_region.csv"),
        "ops_pipeline":  _csv("data", "ops_pipeline.csv"),
        "ops_daily":     _csv("data", "ops_daily.csv"),
        # ── prediction/ — ML & Prophet output ────────────
        "dealer_churn":   _csv("prediction", "dealer_churn.csv"),
        "dealer_activity":_csv("prediction", "dealer_activity.csv"),
        "fcst_daily":     _csv("prediction", "revenue_q2_daily.csv"),
        "fcst_monthly":   _csv("prediction", "revenue_q2_monthly.csv"),
        "color_fcst":     _csv("prediction", "color_q2.csv"),
    }

DATA = load_all()

BRAND = {
    "CITYBIKE_P":  "#1D9E75",
    "KIDBIKE_1":   "#378ADD",
    "KIDBIKE_2":   "#7F77DD",
    "SPORTBIKE_S": "#D85A30",
    "SPORTBIKE_A": "#BA7517",
}
GROUP_NAMES = {
    "CITYBIKE_P":  "Xe phổ thông",
    "KIDBIKE_1":   "Xe trẻ em nhóm 1",
    "KIDBIKE_2":   "Xe trẻ em nhóm 2",
    "SPORTBIKE_S": "Xe thể thao thép",
    "SPORTBIKE_A": "Xe thể thao nhôm",
}