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
        "kpi":            _csv("dashboard", "01_kpi_overview.csv"),
        "monthly":        _csv("dashboard", "02_monthly_trend.csv"),
        "sku":            _csv("dashboard", "03_product_analysis.csv"),
        "color":          _csv("dashboard", "03_color_analysis.csv"),
        "dealer":         _csv("dashboard", "04_dealer_rfm.csv"),
        "province":       _csv("dashboard", "05_geo_province.csv"),
        "region":         _csv("dashboard", "05_geo_region.csv"),
        "ops_pipeline":   _csv("dashboard", "06_ops_pipeline.csv"),
        "ops_daily":      _csv("dashboard", "06_ops_daily.csv"),
        "fcst_daily":     _csv("forecast",  "c1_revenue_q2_daily.csv"),
        "fcst_monthly":   _csv("forecast",  "c1_revenue_q2_monthly.csv"),
        "color_fcst":     _csv("forecast",  "c2_color_q2.csv"),
        "color_hist":     _csv("forecast",  "c2_color_history.csv"),
        "dealer_activity":_csv("forecast",  "c3_dealer_activity.csv"),
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
