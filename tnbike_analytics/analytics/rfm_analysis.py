"""
Phân tích RFM — 702 đại lý Xe đạp Thống Nhất
Cột dùng: customer_code, customer_name, order_date, so_number, line_total
"""
import pandas as pd
import numpy as np

SEGMENT_LABELS = {
    (5, 5): "Champions",
    (5, 4): "Champions",
    (4, 5): "Loyal",
    (4, 4): "Loyal",
    (4, 3): "Loyal",
    (3, 5): "Có tiềm năng",
    (3, 4): "Có tiềm năng",
    (5, 3): "Mới gần đây",
    (5, 2): "Mới gần đây",
    (3, 3): "Cần chú ý",
    (2, 5): "Nguy cơ rời bỏ",
    (2, 4): "Nguy cơ rời bỏ",
    (2, 3): "Nguy cơ rời bỏ",
    (1, 5): "Không thể mất",
    (1, 4): "Không thể mất",
    (2, 2): "Ngủ đông",
    (1, 3): "Ngủ đông",
    (1, 2): "Đã mất",
    (1, 1): "Đã mất",
}


def compute_rfm(df: pd.DataFrame, reference_date=None) -> pd.DataFrame:
    """Tính RFM score cho toàn bộ đại lý trong dataset."""
    if reference_date is None:
        reference_date = df["order_date"].max() + pd.Timedelta(days=1)

    rfm = df.groupby(["customer_code", "customer_name"]).agg(
        last_order =("order_date", "max"),
        freq       =("so_number",  "nunique"),
        monetary   =("line_total", "sum"),
    ).reset_index()

    rfm["recency_days"] = (reference_date - rfm["last_order"]).dt.days

    rfm["R"] = pd.qcut(rfm["recency_days"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["F"] = pd.qcut(rfm["freq"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["M"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["rfm_score"] = rfm["R"] * 100 + rfm["F"] * 10 + rfm["M"]

    rfm["segment"] = rfm.apply(
        lambda r: SEGMENT_LABELS.get((r.R, r.F), "Trung bình"), axis=1
    )
    return rfm


def detect_churn_risk(rfm: pd.DataFrame) -> pd.DataFrame:
    """Lọc đại lý có nguy cơ rời bỏ và tính xác suất churn đơn giản."""
    at_risk = rfm[
        (rfm["R"] <= 2) |
        (rfm["recency_days"] >= 90) |
        rfm["segment"].isin(["Nguy cơ rời bỏ", "Ngủ đông", "Đã mất"])
    ].copy()

    at_risk["churn_prob"] = at_risk.apply(
        lambda r: min(1.0, (r.recency_days / 180.0) * (1 - r.R / 5.0)),
        axis=1
    )
    return at_risk.sort_values("churn_prob", ascending=False)


def segment_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    """Thống kê số lượng và doanh thu theo phân khúc."""
    return (
        rfm.groupby("segment")
        .agg(
            so_dai_ly  =("customer_code", "count"),
            doanh_thu  =("monetary",      "sum"),
            recency_tb =("recency_days",  "mean"),
            freq_tb    =("freq",          "mean"),
        )
        .reset_index()
        .sort_values("doanh_thu", ascending=False)
    )
