"""
Ma trận BCG — Phân loại 5 nhóm sản phẩm tnbike
Trục X: Thị phần doanh thu (%) — relative market share
Trục Y: Tốc độ tăng trưởng YoY Q1 (%)
"""
import pandas as pd


def compute_bcg(df: pd.DataFrame, group_by: str = "group_code") -> pd.DataFrame:
    """
    Tính BCG cho nhóm SP (group_code) hoặc dòng xe (line_name).
    Cần cột: fiscal_year, fiscal_quarter, group_code/line_name, line_total.
    """
    rev_2025    = df[df["fiscal_year"] == 2025].groupby(group_by)["line_total"].sum()
    rev_q1_2026 = df[(df["fiscal_year"] == 2026) & (df["fiscal_quarter"] == 1)].groupby(group_by)["line_total"].sum()
    rev_q1_2025 = df[(df["fiscal_year"] == 2025) & (df["fiscal_quarter"] == 1)].groupby(group_by)["line_total"].sum()

    bcg = pd.DataFrame({
        "rev_2025":    rev_2025,
        "rev_q1_2026": rev_q1_2026,
        "rev_q1_2025": rev_q1_2025,
    }).fillna(0)

    total_2025 = bcg["rev_2025"].sum()
    bcg["market_share_pct"] = (bcg["rev_2025"] / total_2025 * 100).round(1) if total_2025 else 0
    bcg["growth_pct"] = (
        (bcg["rev_q1_2026"] - bcg["rev_q1_2025"]) /
        bcg["rev_q1_2025"].replace(0, 1) * 100
    ).round(1)

    median_share  = bcg["market_share_pct"].median()
    median_growth = bcg["growth_pct"].median()

    def classify(row):
        high_share  = row["market_share_pct"] >= median_share
        high_growth = row["growth_pct"]         >= median_growth
        if high_share  and high_growth:  return "Stars"
        if high_share  and not high_growth: return "Cash Cows"
        if not high_share and high_growth: return "Question Marks"
        return "Dogs"

    bcg["bcg_label"] = bcg.apply(classify, axis=1)
    return bcg.reset_index()
