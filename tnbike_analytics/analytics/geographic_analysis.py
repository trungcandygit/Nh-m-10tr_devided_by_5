"""
Phân tích địa lý — Doanh thu theo 63 tỉnh và 3 miền
Cột: province_name, region, line_total, quantity, fiscal_year, fiscal_quarter
"""
import pandas as pd


def revenue_by_province(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["province_name", "region"])
        .agg(
            doanh_thu   =("line_total",    "sum"),
            so_luong    =("quantity",      "sum"),
            so_don_hang =("so_number",     "nunique"),
            so_dai_ly   =("customer_code", "nunique"),
        )
        .reset_index()
        .sort_values("doanh_thu", ascending=False)
    )


def revenue_by_region_quarter(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["fiscal_year", "fiscal_quarter", "region"])["line_total"]
        .sum().reset_index()
    )


def geo_growth(df: pd.DataFrame) -> pd.DataFrame:
    """Tăng trưởng doanh thu theo tỉnh: Q1/2026 vs Q1/2025."""
    q1_25 = (
        df[(df["fiscal_year"] == 2025) & (df["fiscal_quarter"] == 1)]
        .groupby("province_name")["line_total"].sum()
    )
    q1_26 = (
        df[(df["fiscal_year"] == 2026) & (df["fiscal_quarter"] == 1)]
        .groupby("province_name")["line_total"].sum()
    )
    growth = pd.DataFrame({"q1_2025": q1_25, "q1_2026": q1_26}).fillna(0)
    growth["growth_pct"] = (
        (growth["q1_2026"] - growth["q1_2025"]) /
        growth["q1_2025"].replace(0, 1) * 100
    ).round(1)
    return growth.sort_values("growth_pct", ascending=False).reset_index()


def whitespace_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Tỉnh có đại lý ít — tiềm năng mở rộng thị trường."""
    return (
        df.groupby(["province_name", "region"])
        .agg(
            so_dai_ly   =("customer_code", "nunique"),
            doanh_thu   =("line_total",    "sum"),
            so_don_hang =("so_number",     "nunique"),
        )
        .reset_index()
        .sort_values("so_dai_ly")
    )
