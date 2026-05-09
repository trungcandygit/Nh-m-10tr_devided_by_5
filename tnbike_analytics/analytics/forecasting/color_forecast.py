"""
Dự báo màu sắc / SKU Q2/2026
Cột: color, group_code, fiscal_year, fiscal_month, quantity
"""
import pandas as pd
import numpy as np


def color_share_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Tỷ trọng màu sắc theo tháng trong mỗi nhóm SP."""
    monthly = df.groupby(
        ["fiscal_year", "fiscal_month", "group_code", "color"]
    )["quantity"].sum().reset_index()
    total = monthly.groupby(
        ["fiscal_year", "fiscal_month", "group_code"]
    )["quantity"].transform("sum")
    monthly["share_pct"] = (monthly["quantity"] / total * 100).round(1)
    return monthly


def forecast_color_q2(df: pd.DataFrame) -> pd.DataFrame:
    """
    Dự báo tỷ trọng màu Q2/2026 dùng weighted moving average
    của 3 tháng gần nhất (T1–T3/2026).
    """
    recent = df[(df["fiscal_year"] == 2026) & (df["fiscal_month"].isin([1, 2, 3]))]
    color_qty = recent.groupby(["group_code", "color"])["quantity"].sum()
    total     = color_qty.groupby("group_code").transform("sum")
    forecast  = (color_qty / total * 100).round(1).reset_index()
    forecast.columns = ["group_code", "color", "du_bao_q2_pct"]
    return forecast.sort_values(["group_code", "du_bao_q2_pct"], ascending=[True, False])


def slow_moving_sku(df: pd.DataFrame, threshold_qty: int = 10) -> pd.DataFrame:
    """SKU bán chậm T1–T3/2026 — nguy cơ tồn kho."""
    recent  = df[(df["fiscal_year"] == 2026) & (df["fiscal_month"].isin([1, 2, 3]))]
    sku_qty = recent.groupby(
        ["product_code", "product_name", "color", "group_code"]
    )["quantity"].sum().reset_index()
    slow = sku_qty[sku_qty["quantity"] <= threshold_qty].sort_values("quantity")
    return slow


def top_colors_per_group(df: pd.DataFrame, top_n: int = 3) -> pd.DataFrame:
    """Top N màu sắc theo doanh số trong mỗi nhóm SP."""
    color_rev = df.groupby(["group_code", "color"])["quantity"].sum().reset_index()
    return (
        color_rev.sort_values(["group_code", "quantity"], ascending=[True, False])
        .groupby("group_code").head(top_n)
        .reset_index(drop=True)
    )
