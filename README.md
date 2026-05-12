# TNBike Analytics — DATA EXPLORERS 2026 · Vòng 2

Phân tích & dự báo kinh doanh **Công ty Xe đạp Thống Nhất**  
Q1-2025 → Q1-2026 → T3/2026 | 703 đại lý | 265 SKU | 5 nhóm SP

---

## Quick Start

```bash
cd tnbike_analytics
pip install -r dashboard/requirements.txt
python export_csv.py          # sinh toàn bộ CSV
pytest tests/ -v              # 52 tests → output/test_report.md
cd dashboard && python index.py   # http://localhost:8050
```

---

## Cấu trúc

```
Nh-m-10tr_devided_by_5/
├── README.md
├── de_thi/                        # Đề thi, SQL gốc, .rar email/pdf
└── tnbike_analytics/
    ├── export_csv.py              ← ENTRY POINT
    ├── analytics/
    │   ├── sql_data_loader.py     # SQL → DataFrames (không cần DB)
    │   ├── t3_loader.py           # .eml + .pdf → DataFrame T3/2026
    │   └── prediction_engine.py   # Prophet · K-Means · BG-NBD · LightGBM
    ├── pipeline/                  # Hạng mục A: email → PostgreSQL
    ├── dashboard/                 # Dash 6 trang (port 8050)
    ├── tests/                     # 52 tests
    └── output/
        ├── master/fact_full.csv   # grain: order line (47 cols)
        ├── master/agg_master.csv  # nhiều grain (70 cols)
        ├── data/                  # BI team → 6 CSV
        ├── prediction/            # ML team → 9 CSV
        └── test_report.md
```

---

## Pipeline

```
[02_import_data.sql] ─→ sql_data_loader ─┐
[.eml + .pdf T3]     ─→ t3_loader       ─┴→ build_fact()
                                                   │
              ┌────────────────┬──────────────────┤
              ▼                ▼                  ▼
     Pipeline B (CSV)  Pipeline C — ML    Pipeline A (DB)
     output/data/      run_q1_forecast    pipeline/run_pipeline.py
     output/master/    run_q2_color       → PostgreSQL
                       run_q3_dealer
                       output/prediction/
```

| Pipeline | Làm gì | Cần gì |
|---|---|---|
| **A — Email** | Parse 1.132 .eml/.pdf → ghi DB | PostgreSQL + file email |
| **B — Analytics** | KPI, xu hướng, địa lý, ops → CSV | Chỉ cần SQL file |
| **C — ML/Forecast** | Dự báo Q2, phân cụm, churn → CSV | Chỉ cần SQL file |

---

## Phân chia nhóm

| Nhóm | Dùng file nào | Làm gì |
|---|---|---|
| **BI / Phân tích** | `output/data/` + `agg_master.csv` | Dashboard, báo cáo, KPI |
| **ML / Dự báo** | `output/prediction/` + `fact_full.csv` | Dự báo, churn, phân cụm |

→ Xem chi tiết cột từng file: **[DATA_DICTIONARY.md](DATA_DICTIONARY.md)**

---

## ML / Forecast

| Câu hỏi | Model | Output |
|---|---|---|
| Q1: Doanh số Q2 | Prophet logistic | `revenue_q2_*.csv`, `sku_q2_forecast.csv` |
| Q2: Màu + tồn kho | K-Means k=4 + seasonal trend | `color_q2.csv`, `sku_cluster.csv` |
| Q3: Churn đại lý | LightGBM (AUC=0.843) + SHAP | `dealer_churn.csv`, `shap_importance.csv` |
| Q3: Hoạt động | BG-NBD | `dealer_activity.csv` |

**Không data leakage**: features = Q1-2025 only. Label = active/inactive 2026.

---

## Stack

| | |
|---|---|
| Data | SQL file (không cần PostgreSQL) |
| Forecast | Prophet + VN holidays |
| Churn | LightGBM + SHAP + BG-NBD (lifetimes) |
| Cluster | scikit-learn K-Means |
| Dashboard | Dash 4 / Plotly / DBC |
| Tests | pytest 52 tests |
