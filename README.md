# tnbike_analytics — DATA EXPLORERS 2026 Vòng 2

Hệ thống phân tích & dự báo kinh doanh **Công ty Xe đạp Thống Nhất**  
Phạm vi: Q1-2025 + Q1-2026 + T3/2026 (email pipeline) | 703 đại lý | 265 SKU | 5 nhóm sản phẩm

---

## Cấu trúc dự án

```
Nh-m-10tr_devided_by_5/
│
├── .gitignore
├── README.md
│
├── de_thi/                            # Đề thi + dữ liệu gốc
│   ├── emails/                        # 1.132 file .eml (gitignored)
│   ├── pdfs/                          # 1.132 file .pdf (gitignored)
│   ├── tnbike_emails_mar2026.rar
│   ├── tnbike_pdfs_mar2026.rar
│   ├── 01_create_tables.sql
│   ├── 02_import_data.sql
│   └── DataExplorers2026 - Đề thi Vòng 2 (2).pdf
│
└── tnbike_analytics/
    │
    ├── export_csv.py                  # ENTRY POINT → output/data/ + output/prediction/
    ├── export_master.py               # Pipeline cũ (legacy)
    │
    ├── analytics/
    │   ├── sql_data_loader.py         # Parse sql/02_import_data.sql → DataFrames
    │   ├── t3_loader.py               # Parse 1.132 email+PDF T3/2026 → DataFrame
    │   └── prediction_engine.py       # BG-NBD + LightGBM + Prophet + K-Means
    │
    ├── pipeline/                      # Hạng mục A — Xử lý email + PDF T3/2026
    │   ├── email_parser.py
    │   ├── pdf_extractor.py
    │   ├── validator.py
    │   ├── db_connection.py
    │   ├── db_writer.py
    │   └── run_pipeline.py
    │
    ├── dashboard/                     # Dash app 6 trang (port 8050)
    │   ├── index.py
    │   ├── app.py
    │   ├── data_loader.py
    │   ├── assets/style.css
    │   ├── requirements.txt
    │   └── pages/
    │       ├── p1_overview.py         # KPI + xu hướng doanh thu
    │       ├── p2_product.py          # Pareto, BCG, màu sắc
    │       ├── p3_dealer.py           # RFM + Churn
    │       ├── p4_geo.py              # Tỉnh thành, vùng
    │       ├── p5_forecast.py         # Prophet Q2 + dealer activity
    │       └── p6_ops.py              # Vận hành pipeline email
    │
    ├── sql/
    │   ├── 01_create_tables.sql
    │   ├── 02_import_data.sql
    │   ├── 03_email_log.sql
    │   ├── 04_dim_date.sql
    │   └── 05_views_extra.sql
    │
    ├── tests/
    │   ├── test_analytics.py          # 20 tests — data loading, RFM, aggregation
    │   ├── test_prediction_engine.py  # 32 tests — Q1/Q2/Q3 model validation
    │   ├── test_email_parser.py
    │   ├── test_pdf_extractor.py
    │   └── test_validator.py
    │
    ├── data/
    │   ├── raw/emails/ → ../../de_thi/emails/   # symlink (gitignored)
    │   └── raw/pdfs/   → ../../de_thi/pdfs/     # symlink (gitignored)
    │
    └── output/
        ├── test_report.md             # Kết quả metrics model (tự động sinh sau pytest)
        │
        ├── data/                      # Dữ liệu thực tế — KHÔNG có ML output
        │   ├── raw_history.csv        # 17,031 rows — Q1-2025 + Q1-Feb2026 từ SQL
        │   ├── raw_t3_orders.csv      #  8,559 rows — T3/2026 từ email pipeline
        │   ├── kpi_overview.csv       #     12 rows — 12 KPI tổng hợp
        │   ├── monthly_trend.csv      #     36 rows — tháng × nhóm: DT, SL, YoY, MoM
        │   ├── product_analysis.csv   #    161 rows — SKU: Pareto A/B/C, BCG, YoY
        │   ├── color_analysis.csv     #    328 rows — màu × nhóm × tháng
        │   ├── color_history.csv      #    328 rows — tỷ trọng màu theo tháng
        │   ├── dealer_rfm.csv         #    333 rows — đại lý: RFM features & segments
        │   ├── geo_province.csv       #     74 rows — tỉnh: DT, rank, share
        │   ├── geo_region.csv         #     20 rows — vùng × nhóm SP
        │   ├── ops_pipeline.csv       #      8 rows — thống kê pipeline email T3
        │   └── ops_daily.csv          #     31 rows — DT + đơn mỗi ngày T3/2026
        │
        └── prediction/                # Dữ liệu dự báo & ML output
            ├── revenue_q2_daily.csv   #    924 rows — Prophet: dự báo daily Q2/2026
            ├── revenue_q2_monthly.csv #     45 rows — Prophet: dự báo monthly Q2/2026
            ├── revenue_q2_weekly.csv  #     70 rows — Prophet: dự báo weekly Q2/2026
            ├── sku_q2_forecast.csv    #    363 rows — dự báo SKU Q2 (top20 flag)
            ├── color_q2.csv           #    180 rows — dự báo màu Q2 + seasonal_trend
            ├── sku_cluster.csv        #    161 rows — K-Means: cluster + slow_mover_risk
            ├── dealer_churn.csv       #    333 rows — LightGBM: P(churn), ROC-AUC=0.843
            ├── dealer_activity.csv    #    333 rows — BG-NBD: P(đặt hàng 30 ngày tới)
            └── shap_importance.csv    #      6 rows — SHAP feature importance
```

---

## Output CSV chi tiết

### `output/data/` — Dữ liệu thực tế (12 file)

| File | Rows | Mô tả |
|---|---|---|
| `raw_history.csv` | 17,031 | Order line thô — Q1-2025 + Q1-Feb2026 từ SQL |
| `raw_t3_orders.csv` | 8,559 | Order line thô — T3/2026 từ email pipeline |
| `kpi_overview.csv` | 12 | KPI: doanh thu, đơn hàng, đại lý, T3 stats |
| `monthly_trend.csv` | 36 | Tháng × nhóm SP: DT, SL, YoY, MoM, YTD |
| `product_analysis.csv` | 161 | SKU: Pareto A/B/C, BCG, YoY |
| `color_analysis.csv` | 328 | Màu × nhóm × tháng: DT, SL |
| `color_history.csv` | 328 | Tỷ trọng (%) màu sắc theo tháng |
| `dealer_rfm.csv` | 333 | Đại lý: recency, frequency, monetary, RFM segment |
| `geo_province.csv` | 74 | Tỉnh: DT, rank quốc gia + vùng, share % |
| `geo_region.csv` | 20 | Vùng × nhóm SP |
| `ops_pipeline.csv` | 8 | Pipeline T3: tổng email, OK, lỗi, tỷ lệ |
| `ops_daily.csv` | 31 | Đơn hàng + doanh thu từng ngày T3/2026 |

### `output/prediction/` — Dự báo & ML output (9 file)

| File | Rows | Model | Mô tả |
|---|---|---|---|
| `revenue_q2_daily.csv` | 924 | Prophet | Dự báo daily Q2/2026 × 5 nhóm SP |
| `revenue_q2_monthly.csv` | 45 | Prophet | Tổng hợp tháng × nhóm SP (train + forecast) |
| `revenue_q2_weekly.csv` | 70 | Prophet | Tổng hợp tuần Q2/2026 × nhóm SP |
| `sku_q2_forecast.csv` | 363 | Prophet+share | Dự báo SKU Q2; `top20_flag=1` = 60 rows |
| `color_q2.csv` | 180 | Share-based | Dự báo màu Q2; `seasonal_trend` Tăng/Giảm/Ổn định |
| `sku_cluster.csv` | 161 | K-Means (k=4) | SKU cluster: Ngôi sao/Bò sữa/Dấu hỏi/Bán chậm + `slow_mover_risk` |
| `dealer_churn.csv` | 333 | LightGBM | P(churn), churn_priority, churn_split, ROC-AUC=0.843 |
| `dealer_activity.csv` | 333 | BG-NBD | `prob_purchase_30d`, `expected_orders_30d`, `marketing_priority_label` |
| `shap_importance.csv` | 6 | SHAP | Feature importance của LightGBM churn model |

---

## Cài đặt & Chạy

```bash
pip install -r requirements.txt

# Giải nén dữ liệu email/PDF (nếu chưa có)
cd de_thi
unrar e tnbike_emails_mar2026.rar emails/
unrar e tnbike_pdfs_mar2026.rar   pdfs/

# Sinh toàn bộ CSV (data/ + prediction/)
cd tnbike_analytics
python export_csv.py

# Chạy tests (36 pass → 52 pass sau khi thêm test_prediction_engine)
pytest tests/ -v

# Chạy dashboard (6 trang)
cd dashboard && python index.py
# → http://localhost:8050
```

**Output mẫu `export_csv.py`:**
```
INFO  Loading data...
INFO     T3: 1112 orders OK | 20 lỗi | 8559 order lines | revenue=39,909,335,753
INFO  === DATA/ ===
INFO    raw_history.csv           17,031 rows
INFO    raw_t3_orders.csv          8,559 rows  (1112 orders)
INFO    kpi_overview.csv             12 rows
INFO    ...
INFO    dealer_rfm.csv              333 rows
INFO  === PREDICTION/ ===
INFO    BG-NBD fit: 403 đại lý
INFO    LightGBM churn ROC-AUC test: 0.843
INFO    SHAP top feature: revenue_q1_2025 (importance=0.5333)
INFO    Prophet: 5 nhóm SP
INFO    revenue_q2_daily.csv        924 rows
INFO    revenue_q2_weekly.csv        70 rows
INFO    sku_q2_forecast.csv         363 rows  (top20: 60)
INFO    color_q2.csv               180 rows  (seasonal_trend)
INFO    sku_cluster.csv            161 rows  (slow-mover: 79)
INFO    dealer_churn.csv            333 rows
INFO    dealer_activity.csv         333 rows
INFO    shap_importance.csv           6 rows
```

---

## ML / Forecast

### Q1 — Dự báo doanh số Q2/2026 → `revenue_q2_*.csv` + `sku_q2_forecast.csv`

| Thành phần | Chi tiết |
|---|---|
| **Model** | Prophet (logistic growth, VN holidays, weekly seasonality) |
| **Train** | 2025-01-01 → 2026-03-31 (daily per nhóm SP) |
| **Forecast** | Apr–Jun 2026 (Q2/2026) |
| **Granularity** | Daily → tổng hợp monthly + weekly |
| **Top-20 SKU** | Phân bổ group yhat xuống SKU theo tỷ trọng Q1-2026 |
| **Output** | `yhat`, `yhat_lower`, `yhat_upper`, `split`=train/forecast |

### Q2 — Dự báo màu sắc & phát hiện SKU bán chậm → `color_q2.csv` + `sku_cluster.csv`

| Thành phần | Chi tiết |
|---|---|
| **Seasonal trend** | So sánh tỷ trọng màu Q1-2025 vs Q1-2026: "Tăng/Giảm/Ổn định" (ngưỡng ±0.5%) |
| **K-Means** | k=4 clusters: Ngôi sao / Bò sữa / Dấu hỏi / Bán chậm |
| **Slow-mover** | Cluster "Bán chậm" HOẶC YoY < -10% → `slow_mover_risk` = "Nguy cơ cao" |
| **Features** | revenue, quantity, n_orders, n_months_active, yoy_rev_pct, avg_monthly_rev |

### Q3 — Dự báo hoạt động đại lý → `dealer_activity.csv` + `dealer_churn.csv`

| Thành phần | Chi tiết |
|---|---|
| **BG-NBD** | P(đặt hàng trong 30 ngày tới) + expected_orders_30d |
| **LightGBM** | Churn prediction, ROC-AUC test = **0.843** |
| **SHAP** | Feature importance — top: revenue_q1_2025 |
| **Feature period** | Q1-2025 (≤ 2025-03-31) — không data leakage |
| **Label** | Churn = không mua lại trong 2026 |
| **Split** | 80/20 StratifiedShuffleSplit |
| **Features (6)** | recency_days, n_orders_q1_2025, revenue_q1_2025, avg_order_value, n_product_groups, trend_slope |
| **marketing_priority** | 1=Ưu tiên cao (churn≥0.6 + trend<40), 2=Trung bình, 3=Thấp |

> **Lưu ý data integrity**: `active_in_t3`, `revenue_total`, `n_orders_total` bị loại khỏi features vì dùng data sau FEAT_END — sẽ gây data leakage (test `test_q3_no_leakage_auc_ceiling` kiểm tra AUC < 0.99).

---

## Tests

```
tests/
├── test_analytics.py          # 20 tests — data loading, RFM, aggregation, YoY
├── test_prediction_engine.py  # 32 tests — Q1/Q2/Q3 model validation
├── test_email_parser.py       #  5 tests (8 skip nếu không có .eml)
├── test_pdf_extractor.py      #  6 tests (5 skip nếu không có .pdf)
└── test_validator.py          #  5 tests
```

**Kết quả test_prediction_engine.py (32 tests):**

| Nhóm | Test | Kiểm tra |
|---|---|---|
| Q1 | 8 tests | Columns, groups, date range, yhat≥0, top20 count, revenue bounds |
| Q2 | 8 tests | Seasonal trend labels, cluster labels, slow_mover flags, share sums |
| Q3 | 16 tests | prob∈[0,1], ROC-AUC 0.65–0.99, split 80/20, SHAP count, RFM range |

Metrics được ghi tự động vào `output/test_report.md` sau khi chạy `pytest tests/test_prediction_engine.py`.

---

## Đọc CSV

```python
import pandas as pd

STR_COLS = {"product_code": str}  # giữ leading zeros

# Dữ liệu thực tế
kpi     = pd.read_csv("output/data/kpi_overview.csv")
monthly = pd.read_csv("output/data/monthly_trend.csv")
sku     = pd.read_csv("output/data/product_analysis.csv", dtype=STR_COLS)
dealer  = pd.read_csv("output/data/dealer_rfm.csv")

# Dự báo Q1
fcst_daily   = pd.read_csv("output/prediction/revenue_q2_daily.csv")
fcst_monthly = pd.read_csv("output/prediction/revenue_q2_monthly.csv")
fcst_weekly  = pd.read_csv("output/prediction/revenue_q2_weekly.csv")
sku_q2       = pd.read_csv("output/prediction/sku_q2_forecast.csv", dtype=STR_COLS)

# Dự báo Q2
color_q2    = pd.read_csv("output/prediction/color_q2.csv")
sku_cluster = pd.read_csv("output/prediction/sku_cluster.csv", dtype=STR_COLS)

# Dự báo Q3
churn    = pd.read_csv("output/prediction/dealer_churn.csv")
activity = pd.read_csv("output/prediction/dealer_activity.csv")
shap_imp = pd.read_csv("output/prediction/shap_importance.csv")

# Join dealer RFM + churn + activity (full view)
dealer_full = dealer.merge(churn, on="customer_code", how="left") \
                    .merge(activity[["customer_code","prob_purchase_30d",
                                     "expected_orders_30d","marketing_priority_label"]],
                           on="customer_code", how="left")
```

---

## Pipeline A — Xử lý email T3/2026

Yêu cầu: PostgreSQL + file .eml/.pdf trong `data/raw/`

```bash
cp .env.example .env   # sửa thông tin PostgreSQL
psql -U postgres -d tnbike_db -f sql/01_create_tables.sql
psql -U postgres -d tnbike_db -f sql/02_import_data.sql
psql -U postgres -d tnbike_db -f sql/03_email_log.sql

python -m pipeline.run_pipeline \
  --email-dir data/raw/emails \
  --pdf-dir   data/raw/pdfs
```

---

## Schema

| Bảng | Mô tả |
|---|---|
| `product_group` | 5 nhóm sản phẩm |
| `product_line` | 72 dòng xe |
| `product` | 247 SKU |
| `province` | 63 tỉnh thành |
| `customer` | 702 đại lý |
| `sales_order` | Đầu phiếu bán hàng |
| `order_line` | Dòng hàng hóa |
| `email_log` | Log pipeline A |

**5 nhóm sản phẩm:**

| Code | Tên |
|---|---|
| `CITYBIKE_P` | Xe phổ thông |
| `KIDBIKE_1` | Xe trẻ em nhóm 1 |
| `KIDBIKE_2` | Xe trẻ em nhóm 2 |
| `SPORTBIKE_S` | Xe thể thao khung thép |
| `SPORTBIKE_A` | Xe thể thao khung nhôm |

---

## Stack

| Layer | Công nghệ |
|---|---|
| Data source | SQL file (không cần DB để analytics) |
| Email pipeline | Python `email`, pdftotext (poppler) |
| Forecast | Prophet (logistic growth + VN holidays) |
| Churn / Activity | LightGBM + SHAP + BG-NBD (lifetimes) |
| SKU segmentation | K-Means (scikit-learn) |
| Dashboard | Dash 4.x / Plotly + Dash Bootstrap Components |
| Tests | pytest — 32 model tests + 20 analytics tests |
