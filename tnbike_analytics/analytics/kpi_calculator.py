"""
Tính toán 6 nhóm KPI — Dữ liệu fact_sales tnbike 2025–T3/2026
"""
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def get_engine():
    from config import DB_URL, DB_SCHEMA
    from sqlalchemy import create_engine
    return create_engine(DB_URL, connect_args={"options": f"-c search_path={DB_SCHEMA},public"})


def load_fact_sales() -> pd.DataFrame:
    engine = get_engine()
    q = "SELECT * FROM fact_sales ORDER BY order_date"
    df = pd.read_sql(q, engine)
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["ym"] = df["fiscal_year"].astype(str) + "-" + df["fiscal_month"].astype(str).str.zfill(2)
    return df


def kpi_san_luong(df: pd.DataFrame) -> dict:
    return {
        "tong_so_luong_ban":    int(df["quantity"].sum()),
        "tong_don_hang":        df["so_number"].nunique(),
        "dong_hang_tb_moi_don": round(df.groupby("so_number")["quantity"].sum().mean(), 1),
        "tb_sp_moi_don":        round(df.groupby("so_number").size().mean(), 1),
    }


def kpi_doanh_thu(df: pd.DataFrame) -> dict:
    total_rev = df["line_total"].sum()
    n_dealers = df["customer_code"].nunique()
    total_qty = df["quantity"].sum()
    return {
        "tong_doanh_thu":          total_rev,
        "gia_ban_trung_binh":      round(total_rev / total_qty, 0) if total_qty else 0,
        "doanh_thu_tb_moi_dai_ly": round(total_rev / n_dealers, 0) if n_dealers else 0,
        "tong_dai_ly_hoat_dong":   n_dealers,
    }


def kpi_tang_truong(df: pd.DataFrame) -> pd.DataFrame:
    monthly = (
        df.groupby(["fiscal_year", "fiscal_month"])["line_total"]
        .sum().reset_index().sort_values(["fiscal_year", "fiscal_month"])
    )
    monthly["mom_pct"] = monthly["line_total"].pct_change() * 100
    monthly["label"]   = monthly.apply(
        lambda r: f"T{r.fiscal_month}/{str(r.fiscal_year)[2:]}", axis=1
    )
    return monthly


def kpi_co_cau_sp(df: pd.DataFrame) -> pd.DataFrame:
    total = df["line_total"].sum()
    result = df.groupby(["group_code", "group_name"]).agg(
        doanh_thu   =("line_total", "sum"),
        so_luong    =("quantity",   "sum"),
        so_don_hang =("so_number",  "nunique"),
        gia_tb      =("unit_price", "mean"),
    ).reset_index()
    result["ty_trong_pct"] = (result["doanh_thu"] / total * 100).round(1)
    return result.sort_values("doanh_thu", ascending=False)


def kpi_dai_ly(df: pd.DataFrame) -> dict:
    by_customer = df.groupby("customer_code")["line_total"].sum().sort_values(ascending=False)
    total = by_customer.sum()
    n     = len(by_customer)
    top20 = by_customer.head(max(1, int(n * 0.2))).sum()
    return {
        "tong_dai_ly":        n,
        "top20pct_chiem_pct": round(top20 / total * 100, 1) if total else 0,
        "top5_chiem_pct":     round(by_customer.head(5).sum() / total * 100, 1) if total else 0,
    }


def kpi_van_hanh() -> dict:
    import json
    from pathlib import Path
    p = Path(__file__).parent.parent / "data/processed/pipeline_result.json"
    if not p.exists():
        return {"trang_thai": "Chưa chạy pipeline"}
    result = json.loads(p.read_text())
    total  = result.get("tong_file", 1)
    ok     = result.get("thanh_cong", 0)
    return {
        "tong_file":         total,
        "thanh_cong":        ok,
        "ti_le_thanh_cong":  round(ok / total * 100, 1) if total else 0,
        "loi_invalid":       result.get("loi_invalid", 0),
        "canh_bao":          result.get("canh_bao", 0),
        "thoi_gian_tb_giay": result.get("thoi_gian_tb_giay", 0),
    }
