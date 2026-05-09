"""
Dự báo doanh số Q2/2026 theo nhóm sản phẩm
Mô hình: Prophet (trend + seasonality VN)
Train: 2025-01 → 2026-03 | Forecast: 2026-04 → 2026-06
"""
import pandas as pd
import logging
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = logging.getLogger("tnbike.forecast.demand")


def prepare_series(df: pd.DataFrame, group_code: str) -> pd.DataFrame:
    """Chuẩn bị time series daily cho 1 nhóm SP → prophet format (ds, y)."""
    sub = df[df["group_code"] == group_code].copy()
    ts  = sub.groupby("order_date")["line_total"].sum().reset_index()
    ts.columns = ["ds", "y"]
    ts["ds"] = pd.to_datetime(ts["ds"])
    return ts.sort_values("ds")


def forecast_group(ts: pd.DataFrame, periods: int = 91) -> pd.DataFrame:
    """Chạy Prophet cho 1 nhóm SP, trả về forecast df."""
    from prophet import Prophet
    # Dùng logistic growth với floor=0 để không dự báo âm
    ts = ts.copy()
    cap   = ts["y"].max() * 2.5
    ts["cap"]   = cap
    ts["floor"] = 0.0

    model = Prophet(
        growth                  = "logistic",
        yearly_seasonality      = True,
        weekly_seasonality      = False,
        seasonality_mode        = "multiplicative",
        changepoint_prior_scale = 0.15,
    )
    model.add_country_holidays(country_name="VN")
    model.fit(ts)

    future          = model.make_future_dataframe(periods=periods)
    future["cap"]   = cap
    future["floor"] = 0.0
    forecast = model.predict(future)
    # Clip phòng trường hợp con số âm nhỏ từ interval
    for col in ["yhat", "yhat_lower", "yhat_upper"]:
        forecast[col] = forecast[col].clip(lower=0)
    return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]


def forecast_all_groups(df: pd.DataFrame) -> dict:
    """Dự báo cho cả 5 nhóm SP, trả về {group_code: forecast_df}."""
    from config import PRODUCT_GROUPS
    results = {}
    for group_code, group_name in PRODUCT_GROUPS.items():
        ts = prepare_series(df, group_code)
        if len(ts) < 10:
            logger.warning(f"Không đủ data cho {group_code}")
            continue
        logger.info(f"Dự báo {group_name} ({len(ts)} ngày)...")
        try:
            fc = forecast_group(ts)
            fc["group_code"] = group_code
            fc["group_name"] = group_name
            results[group_code] = fc
        except Exception as e:
            logger.error(f"Lỗi forecast {group_code}: {e}")
    return results


def aggregate_q2_forecast(results: dict) -> pd.DataFrame:
    """Tổng hợp dự báo Q2/2026 (T4-T6) theo nhóm SP."""
    rows = []
    for group_code, fc in results.items():
        q2 = fc[(fc["ds"] >= "2026-04-01") & (fc["ds"] <= "2026-06-30")]
        rows.append({
            "group_code":    group_code,
            "group_name":    fc["group_name"].iloc[0] if len(fc) else "",
            "du_bao_q2":     q2["yhat"].sum(),
            "lower_bound":   q2["yhat_lower"].sum(),
            "upper_bound":   q2["yhat_upper"].sum(),
        })
    return pd.DataFrame(rows)
